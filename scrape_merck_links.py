import requests
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/'
}

url = "https://www.merckgroup.com/en/news.html"

try:
    r = requests.get(url, headers=headers, timeout=20)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        # Extract all hrefs
        links = re.findall(r'href=["\'](.*?)["\']', r.text)
        # Filter for any links that look like articles
        filtered = [l for l in links if '2024' in l or '2023' in l or '2022' in l]
        for l in sorted(list(set(filtered))):
            print(l)
except Exception as e:
    print(f"Error: {e}")
