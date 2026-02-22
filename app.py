import streamlit as st
import pandas as pd
import requests
import time
import os
from dotenv import load_dotenv
import io
from google import genai

# Load environment variables
load_dotenv()

# === CONFIGURATION ===
SERPER_API_KEY = os.getenv('SERPER_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Initialize Gemini Client
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

# === HEADERS ===
SERPER_HEADERS = {
    "X-API-KEY": SERPER_API_KEY,
    "Content-Type": "application/json"
}

# === LOGIC FUNCTIONS ===

def get_linkedin_links(company_name):
    # Refined query to avoid affiliated companies like "Tesla Power USA"
    # Adding "Inc" or similar can help but can also miss. Using quotes around the name is good.
    # We'll stick to a broader search but give more context to Gemini.
    query = f'site:linkedin.com/in "{company_name}" (Owner OR Founder OR Co-founder OR CEO OR Managing Director)'
    url = "https://google.serper.dev/search"
    body = {
        "q": query,
        "num": 10
    }
    try:
        response = requests.post(url, json=body, headers=SERPER_HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        links = []
        for result in data.get("organic", []):
            link = result.get("link", "")
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            if "linkedin.com/in" in link:
                # Include snippet for more context to Gemini
                links.append(f"Title: {title} | Link: {link} | Snippet: {snippet}")
        return links, None
    except Exception as e:
        return [], f"Search error: {str(e)}"

def pick_best_profile(company, profiles):
    if not profiles:
        return "No profiles found", None

    prompt = f"""You are a research assistant.

Given the company "{company}", and the following LinkedIn profiles found via search:
{chr(10).join(profiles)}

Which one is most likely the **CURRENT** Founder, CEO, or top primary executive of the company "{company}"? 

### GUIDELINES:
1. **EXACT MATCH**: Favor the primary company "{company}". For example, if searching for 'Tesla', favor 'Tesla, Inc.' or 'Tesla' over 'Tesla Power USA'.
2. **CURRENT ONLY**: Prioritize roles that indicate "Current" or "Present". Avoid "Former" or "Past" unless it's a very prominent founder.
3. **SMART REASONING**: If you see a globally recognized leader for a famous company name (e.g., Elon Musk for Tesla), prioritize that profile.
4. **BEST GUESS**: If you are unsure, pick the profile that is most likely to be the leader of the primary company represented by that name.

Return ONLY the URL of the best LinkedIn profile. Avoid any additional text.
"""

    try:
        # Prioritize the model the user confirmed works, then modern flash models
        model_names = [
            "gemini-3-flash-preview", 
            "gemini-2.0-flash", 
            "gemini-1.5-flash", 
            "gemini-1.5-pro",
        ]
        
        last_error = None
        for name in model_names:
            retry_attempts = 3
            backoff = 2
            
            for attempt in range(retry_attempts):
                try:
                    response = client.models.generate_content(
                        model=name,
                        contents=prompt
                    )
                    return response.text.strip(), None
                except Exception as inner_e:
                    last_error = inner_e
                    err_str = str(inner_e).lower()
                    
                    # If it's a rate limit error, wait and retry
                    if "429" in err_str or "resource_exhausted" in err_str:
                        if attempt < retry_attempts - 1:
                            time.sleep(backoff * (attempt + 1))
                            continue
                        else:
                            break # Move to next model if this one is exhausted
                    
                    # If it's a 404/Unsupported, move to next model immediately
                    if "not found" in err_str or "unsupported" in err_str:
                        break 
                    
                    # For other errors, don't retry, just move to next model
                    break
        
        error_msg = str(last_error)
        return "Gemini Error", f"Gemini API Error: {error_msg}"
    except Exception as e:
        return "Gemini Error", f"Gemini API Error: {str(e)}"

# === STREAMLIT UI ===

st.set_page_config(page_title="LinkedIn Executive Scraper", page_icon="🔍")

st.title("🔍 LinkedIn Executive Scraper")
st.markdown("""
Find the most likely **Founder, CEO, or Owner** LinkedIn profile for any company.
""")

# Check for API keys
if not SERPER_API_KEY or not GEMINI_API_KEY:
    st.error("⚠️ API Keys missing! Please ensure `SERPER_API_KEY` and `GEMINI_API_KEY` are set in your `.env` file.")
    st.stop()

# Helper for processing a list of companies
def process_scraping(company_list):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for index, company in enumerate(company_list):
        status_text.text(f"Processing: {company} ({index+1}/{len(company_list)})")
        
        profiles, error = get_linkedin_links(company)
        error_msg = error
        best_profile = "Search Failed"
        
        if not error:
            best_profile, ai_error = pick_best_profile(company, profiles)
            if ai_error:
                error_msg = ai_error
        
        results.append({
            "Company": company,
            "Best LinkedIn URL": best_profile,
            "Error": error_msg or ""
        })
        
        progress_bar.progress((index + 1) / len(company_list))
        time.sleep(1.0) # Increased delay to be kind to the API quota
        
    status_text.text("✅ Processing complete!")
    return pd.DataFrame(results)

# UI Tabs
tab1, tab2 = st.tabs(["🚀 Bulk Search (CSV)", "🔍 Single Search"])

with tab1:
    uploaded_file = st.file_uploader("Upload Companies CSV", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        if 'Company' not in df.columns:
            st.error("CSV must have a column named 'Company'")
        else:
            st.write(f"Loaded {len(df)} companies.")
            if st.button("Start Bulk Scraping"):
                results_df = process_scraping(df['Company'].tolist())
                st.subheader("Results")
                st.dataframe(results_df)
                
