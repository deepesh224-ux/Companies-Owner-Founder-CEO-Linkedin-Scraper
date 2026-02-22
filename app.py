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
