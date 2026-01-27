import requests

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
urls = [
    "https://www.merckgroup.com/en/news/press-releases/2024/07/22/surface-solutions-divestment.html",
    "https://www.merckgroup.com/en/news/press-releases/2024/07/25/surface-solutions-divestment.html",
    "https://www.merckgroup.com/en/news/2024/07/22/surface-solutions-divestment.html",
    "https://www.merckgroup.com/en/news/2024/07/25/surface-solutions-divestment.html"
]

for url in urls:
    try:
        r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        print(f"URL: {url} -> Status: {r.status_code} -> Final: {r.url}")
    except Exception as e:
        print(f"URL: {url} -> Error: {e}")
