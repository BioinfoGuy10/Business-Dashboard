import requests
from duckduckgo_search import DDGS
import json
import time

def check_link(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.status_code == 200
    except:
        return False

def find_real_links():
    # Focused search for the most recent one
    q = 'Merck KGaA "Surface Solutions" divestment July 2024 news'
    print(f"Searching for: {q}")
    
    with DDGS() as ddgs:
        try:
            results = list(ddgs.text(q, max_results=5))
            for res in results:
                url = res['href']
                print(f"Found URL: {url}")
                if check_link(url):
                    print(f"✅ WORKING: {url}")
                else:
                    print(f"❌ BROKEN: {url}")
        except Exception as e:
            print(f"Search failed: {e}")

if __name__ == "__main__":
    find_real_links()
