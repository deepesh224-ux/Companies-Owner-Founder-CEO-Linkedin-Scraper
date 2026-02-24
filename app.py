import sys
try:
    import imghdr
except ImportError:
    # imghdr was removed in Python 3.13, monkeypatching for Streamlit
    import types
    m = types.ModuleType("imghdr")
    m.what = lambda file, h=None: None
    sys.modules["imghdr"] = m

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

# === PAGE CONFIG ===
st.set_page_config(
    page_title="Executive Scraper v3",
    page_icon="Search",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === INITIALIZE STATE ===
if 'history' not in st.session_state:
    st.session_state.history = []

# === CUSTOM CSS (Hyper-Premium) ===
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .stApp {
        background: radial-gradient(circle at top right, #1a1f2c, #0e1117);
    }
    
    /* Premium Metric Style */
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        background: -webkit-linear-gradient(#4fd1c5, #238636);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Glass Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 2rem;
        border-radius: 16px;
        backdrop-filter: blur(20px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        margin-bottom: 25px;
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        border: 1px solid rgba(79, 209, 197, 0.3);
        background: rgba(255, 255, 255, 0.05);
    }

    .icebreaker-box {
        background: rgba(79, 209, 197, 0.05);
        border-left: 4px solid #4fd1c5;
        padding: 1.25rem;
        border-radius: 8px;
        margin-top: 15px;
        font-size: 0.95rem;
        color: #e6edf3;
    }
    
    .confidence-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
        background: rgba(79, 209, 197, 0.2);
        color: #4fd1c5;
        border: 1px solid rgba(79, 209, 197, 0.3);
        margin-bottom: 10px;
    }
    
    /* Quick Try Buttons */
    .stButton>button {
        transition: transform 0.1s active;
    }
    
    .quick-try-label {
        font-size: 0.8rem;
        color: #8b949e;
        margin-bottom: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# === SIDEBAR CONFIGURATION ===
with st.sidebar:
    st.image("https://img.icons8.com/external-flatart-icons-outline-flatarticons/128/4fd1c5/external-search-marketing-flatart-icons-outline-flatarticons.png", width=60)
    st.title("Control Panel")
    
    st.markdown("---")
    
    # API Verification
    serper_key = os.getenv('SERPER_API_KEY')
    gemini_key = os.getenv('GEMINI_API_KEY')
    
    if not serper_key or not gemini_key:
        st.error("Keys Missing in .env")
    else:
        st.success("Processing Node: Online")

    st.markdown("---")
    
    # Persona Selection
    st.subheader("Active Persona")
    personas = {
        "Executive Strategy": "Owner OR Founder OR Co-founder OR CEO OR Managing Director",
        "Technical Leadership": "CTO OR 'VP of Engineering' OR 'Head of Engineering' OR Founder",
        "Growth & Sales": "'VP of Sales' OR 'Head of Sales' OR 'Director of Sales' OR Founder"
    }
    selected_persona = st.selectbox("Active Persona", list(personas.keys()), label_visibility="collapsed")
    persona_query = personas[selected_persona]

    st.markdown("---")
    
    # History
    if st.session_state.history:
        st.subheader("Search History")
        for item in reversed(st.session_state.history[-5:]):
            st.caption(f"• {item}")

    st.markdown("---")
    st.caption("v3.0.2 Dashboard • Secure Tier")

# Initialize Gemini Client
client = None
if gemini_key:
    client = genai.Client(api_key=gemini_key)

# === LOGIC FUNCTIONS ===

def get_linkedin_links(company_name, query_roles):
    query = f'site:linkedin.com/in "{company_name}" ({query_roles})'
    url = "https://google.serper.dev/search"
    body = {"q": query, "num": 10}
    headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=body, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        links = []
        for result in data.get("organic", []):
            link = result.get("link", "")
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            if "linkedin.com/in" in link:
                links.append(f"Title: {title} | Link: {link} | Snippet: {snippet}")
        return links, None
    except Exception as e:
        return [], str(e)

def pick_best_profile(company, profiles):
    if not profiles:
        return None, None, 0, "No profiles found"

    prompt = f"""Analyze the following LinkedIn results for "{company}". Find the primary leader matching the target profile.

{chr(10).join(profiles)}

### REQUIRED JSON RESPONSE:
Return ONLY a JSON object:
{{
  "url": "linkedin URL",
  "icebreaker": "1-sentence cold intro",
  "confidence": "score between 0-100"
}}
"""

    try:
        model_names = ["gemini-3-flash-preview", "gemini-2.0-flash", "gemini-1.5-flash"]
        for name in model_names:
            try:
                response = client.models.generate_content(
                    model=name, 
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                data = response.parsed
                if not data: # Fallback for some models
                    import json
                    data = json.loads(response.text.strip())
                return data["url"], data["icebreaker"], data["confidence"], None
            except:
                continue
        return "Search Failed", "N/A", 0, "AI Analysis Error"
    except Exception as e:
        return "Error", "N/A", 0, str(e)

# === MAIN UI ===

col_logo, col_title = st.columns([1, 12])
with col_logo:
    st.image("https://img.icons8.com/fluency/96/crown.png", width=60)
with col_title:
    st.title("Executive Scraper v3")
    st.caption("Hyper-Precision Intelligence Dashboard")

tab1, tab2 = st.tabs(["Bulk Intelligence", "Instant Discovery"])

with tab1:
    m1, m2, m3 = st.columns(3)
    
    uploaded_file = st.file_uploader("Drop company list here", type=["csv"], label_visibility="collapsed")
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        if 'Company' in df.columns:
            m1.metric("Companies", len(df))
            
            if st.button("Unlock All Insights", use_container_width=True):
                results = []
                progress = st.progress(0)
                success_count = 0
                
                with st.status("Initializing High-Speed Scrape...", expanded=True) as status_box:
                    for i, company in enumerate(df['Company']):
                        status_box.update(label=f"Analyzing {company}...", state="running")
                        
                        profiles, err = get_linkedin_links(company, persona_query)
                        url, summary, conf, ai_err = pick_best_profile(company, profiles)
                        
                        if url and "linkedin.com" in str(url):
                            success_count += 1
                        
                        results.append({
                            "Company": company,
                            "Profile URL": url,
                            "Icebreaker": summary,
                            "Confidence": conf,
                            "Log": (err or ai_err or "OK")
                        })
                        
                        # Update metrics live
                        m2.metric("Verified", success_count)
                        m3.metric("Precision", f"{(success_count/(i+1)*100):.1f}%")
                        progress.progress((i + 1) / len(df))
                        time.sleep(1)
                        
                    status_box.update(label="Intelligence Gathered!", state="complete", expanded=False)
                
                res_df = pd.DataFrame(results)
                st.dataframe(res_df, use_container_width=True, height=400)
                
                csv = res_df.to_csv(index=False).encode('utf-8')
                st.download_button("Export Intelligence", data=csv, file_name="executive_research.csv", mime="text/csv")
        else:
            st.error("Error: CSV must contain a 'Company' column.")

with tab2:
    col_input, col_examples = st.columns([3, 1])
    
    with col_input:
        target = st.text_input("Company Domain or Name", placeholder="e.g. OpenAI", key="itarget")
    
    with col_examples:
        st.markdown('<p class="quick-try-label">Quick Try:</p>', unsafe_allow_html=True)
        ex_cols = st.columns(3)
        if ex_cols[0].button("Stripe"): target = "Stripe"
        if ex_cols[1].button("SpaceX"): target = "SpaceX"
        if ex_cols[2].button("Nvidia"): target = "Nvidia"

    if st.button("Start Discovery", type="primary", use_container_width=True) or (target and target != st.session_state.get('last_search')):
        if target:
            st.session_state.last_search = target
            with st.status(f"Scanning the web for {target}...") as status:
                profiles, err = get_linkedin_links(target, persona_query)
                status.write("Results retrieved. Performing AI analysis...")
                url, summary, conf, ai_err = pick_best_profile(target, profiles)
                status.update(label="Analysis Finished", state="complete")
            
            if url and "linkedin.com" in str(url):
                # Update history
                if target not in st.session_state.history:
                    st.session_state.history.append(target)
                
                st.markdown(f"""
                    <div class="glass-card">
                        <div class="confidence-badge">Confidence: {conf}%</div>
                        <h2 style="margin-top:0">{target} Leadership Identified</h2>
                        <p style="font-size:1.1rem"><b>Target:</b> <a href="{url}" target="_blank" style="color:#4fd1c5">{url}</a></p>
                        <div class="icebreaker-box">
                            <b>Cold Outreach Suggestion:</b><br>
                            "{summary}"
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Discovery failed. The profile might be private or the company name is too broad.")
