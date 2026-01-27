import requests, re
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
url = "https://www.merckgroup.com/en/news.html"
try:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    # Search for "Surface Solutions" in the text and see the surrounding HTML
    matches = re.findall('(<a[^>]*?Surface Solutions[^>]*?>)', r.text, re.IGNORECASE)
    for m in matches:
        print(m)
except Exception as e:
    print(f"Error: {e}")
