import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0") 
TIMEOUT = int(os.getenv("timeout", 30000))
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:3080")

HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": f"{BASE_URL}/pustaka/",
    "HX-Request": "true",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,id;q=0.8"
}