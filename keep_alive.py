"""
Keep-alive script for Render free tier
Pings the backend every 14 minutes to prevent sleep
"""
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "https://clinic-voice-agent.onrender.com")

try:
    response = requests.get(f"{BACKEND_URL}/")
    print(f"Ping successful: {response.status_code} - {response.json()}")
except Exception as e:
    print(f"Ping failed: {e}")
