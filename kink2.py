import requests
import pandas as pd
import time
import random


# === SET YOUR KEYS HERE ===
SERPER_API_KEY = "SERPER_API_KEY"
GITHUB_GPT_TOKEN = "GITHUB_GPT_TOKEN"
GITHUB_GPT_ENDPOINT = "https://models.github.ai/inference/chat/completions"
MODEL_NAME = "openai/gpt-4o-mini"


# === SETTINGS ===
DEBUG = True
ROLE_KEYWORDS = ["Founder", "Co-founder", "CEO", "Managing Director","Owner"]


# === HEADERS ===
SERPER_HEADERS = {
   "X-API-KEY": SERPER_API_KEY,
   "Content-Type": "application/json"
}


GITHUB_HEADERS = {
   "Authorization": f"Bearer {GITHUB_GPT_TOKEN}",
   "Content-Type": "application/json"
}


# === Get LinkedIn profiles using Serper.dev ===
def get_linkedin_links(company_name):
   query = f'site:linkedin.com/in "{company_name}" (Owner OR Founder OR Co-founder OR CEO OR Managing Director OR Owner)'
   url = "https://google.serper.dev/search"
   body = {
       "q": query,
       "num": 10
   }


   try:
       response = requests.post(url, json=body, headers=SERPER_HEADERS, timeout=10)
       response.raise_for_status()
       data = response.json()
       if DEBUG:
           print(f"🔍 Search results for {company_name}:\n", data)
       links = []
       for result in data.get("organic", []):
           link = result.get("link", "")
           title = result.get("title", "")
           if "linkedin.com/in" in link:
               links.append(f"{title} - {link}")
               if DEBUG:
                   print(f"✅ Found profile: {link}")
       return links, None
   except Exception as e:
       return [], f"Search error: {str(e)}"


# === Use GitHub-hosted GPT API to pick best profile ===
def pick_best_profile(company, profiles):
   if not profiles:
       return "No profiles found", None


   prompt = f"""You are a research assistant.


Given the company "{company}", and the following LinkedIn profiles:
{chr(10).join(profiles)}


Which one is most likely the current Founder, Owner, Co-founder, CEO, or Managing Director of the company?


Return ONLY the best LinkedIn URL."""


   payload = {
       "model": MODEL_NAME,
       "messages": [
           {"role": "system", "content": "You are a helpful assistant."},
           {"role": "user", "content": prompt}
       ],
       "temperature": 0.2,
       "max_tokens": 500,
       "top_p": 1.0
   }


   try:
       response = requests.post(GITHUB_GPT_ENDPOINT, headers=GITHUB_HEADERS, json=payload, timeout=20)
       response.raise_for_status()
       data = response.json()
       if DEBUG:
           print(f"🧠 GPT response: {data}")
       return data["choices"][0]["message"]["content"].strip(), None
   except Exception as e:
       return "OpenAI Error", f"OpenAI API Error: {str(e)}"


# === Main CSV Processing Loop ===
def process_companies(input_csv, output_csv):
   df = pd.read_csv(input_csv)
   output_data = []


   for index, row in df.iterrows():
       company = row['Company']
       print(f"\n🔎 Processing: {company}")
       error_msg = None


       try:
           profiles, error = get_linkedin_links(company)
           if error:
               best_profile = "Search Failed"
               error_msg = error
           else:
               best_profile, ai_error = pick_best_profile(company, profiles)
               if ai_error:
                   error_msg = ai_error
       except Exception as e:
           best_profile = "Unknown Failure"
           error_msg = f"Unexpected Error: {str(e)}"


       output_data.append({
           "Company": company,
           "Best LinkedIn URL": best_profile,
           "Error": error_msg or ""
       })


       time.sleep(1)  # Avoid hitting rate limits


   pd.DataFrame(output_data).to_csv(output_csv, index=False)
   print(f"\n✅ Results saved to: {output_csv}")


# === Run ===
process_companies("companies.csv", "founders_ceos_linkedin.csv")


