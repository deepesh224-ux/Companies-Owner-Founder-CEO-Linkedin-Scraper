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
