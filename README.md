# Companies-Owner-Founder-CEO-Linkedin-Scraper
This project automates executive research by extracting LinkedIn profiles of company leaders (CEO, Founder, etc.) using Serper API for search and GitHub-hosted GPT for selection. It processes a company list from CSV and outputs the most relevant profile links into a new CSV file.

- Send this query to **Serper API** → get structured JSON search results.  
- Collect only `linkedin.com/in/...` profile links.  

✅ *Example:* For Tesla →  
- `Elon Musk – linkedin.com/in/elonmusk`  
- `Random Engineer – linkedin.com/in/john-smith`  

---

## 3. Pick Best Profile (`pick_best_profile`)
- Send all LinkedIn results + company name to **GitHub GPT API**.  
- Prompt asks GPT:  
*“Which profile is most likely the Founder/CEO/Owner?”*  
- GPT returns just one LinkedIn URL (best match).  

✅ *Example:* For Tesla →  
- `https://linkedin.com/in/elonmusk`

---

## 4. CSV Processing Loop (`process_companies`)
- Read `companies.csv`.  
- For each company:  
1. Get candidate profiles (via Serper).  
2. Select best match (via GPT).  
3. Handle errors gracefully.  
- Save results in `founders_ceos_linkedin.csv` with columns:  
- `Company`  
- `Best LinkedIn URL`  
- `Error`  

---

## 5. Rate Limit Handling
- Adds `time.sleep(1)` between requests → prevents API blocks.  

---

# 🌐 APIs Explained

### 🔹 Serper API
- A JSON wrapper around Google Search.  
- **Input:** `"site:linkedin.com/in Tesla CEO"`  
- **Output:** Structured results (title, link, snippet).  
- Used to collect candidate LinkedIn URLs.  

### 🔹 GitHub AI API
- Proxy endpoint to use OpenAI models (e.g., `gpt-4o-mini`).  
- **Endpoint:** `https://models.github.ai/inference/chat/completions`  
- **Input:** Prompt + messages.  
- **Output:** AI reasoning (best LinkedIn profile).  

---

# ⚖️ Why Use Both?
- **Serper = Data collection** (find possible profiles).  
- **GitHub AI = Data interpretation** (choose the right profile).  

✅ In short:  
- *Serper = Google Search in JSON.*  
- *GitHub AI = Smart filtering with GPT.*  
