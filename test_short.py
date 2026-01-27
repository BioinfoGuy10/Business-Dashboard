import requests

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
urls = [
    "https://www.merckgroup.com/en/news/2024/07/25/surface-solutions-divestment.html",
    "https://www.merckgroup.com/en/news/2024/05/23/mirus-bio-acquisition.html",
    "https://www.merckgroup.com/en/news/2024/03/07/annual-report-2023.html",
    "https://www.merckgroup.com/en/news/2023/11/23/ceo-reappointment.html"
]

for url in urls:
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"URL: {url} -> Status: {r.status_code}")
    except Exception as e:
        print(f"URL: {url} -> Error: {e}")
