"""
Quick test: verify Google Custom Search API key + CSE ID work.
Run from multi-agent/:  python test_google_search.py
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
CSE_ID  = os.getenv("GOOGLE_CSE_ID")
QUERY   = "newest AI agent frameworks 2026"
ENDPOINT = "https://www.googleapis.com/customsearch/v1"

print(f"API_KEY : {API_KEY[:10]}...{API_KEY[-4:] if API_KEY else 'NOT SET'}")
print(f"CSE_ID  : {CSE_ID or 'NOT SET'}")
print(f"Query   : {QUERY}\n")

if not API_KEY or not CSE_ID:
    print("ERROR: GOOGLE_API_KEY or GOOGLE_CSE_ID not set in .env")
    raise SystemExit(1)

params = {"key": API_KEY, "cx": CSE_ID, "q": QUERY, "num": 3}

try:
    resp = httpx.get(ENDPOINT, params=params, timeout=15)
    print(f"HTTP status : {resp.status_code}")

    if resp.status_code != 200:
        print(f"ERROR body  : {resp.text[:500]}")
        raise SystemExit(1)

    data = resp.json()
    items = data.get("items", [])

    if not items:
        print("No results returned — check CSE configuration (sites to search).")
    else:
        print(f"Got {len(items)} result(s):\n")
        for i, item in enumerate(items, 1):
            print(f"  {i}. {item.get('title')}")
            print(f"     {item.get('link')}")
            print(f"     {item.get('snippet', '')[:120]}\n")

except httpx.RequestError as e:
    print(f"Network error: {e}")
    raise SystemExit(1)
