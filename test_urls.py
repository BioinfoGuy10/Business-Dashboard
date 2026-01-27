import requests

urls_to_test = [
    "https://www.merckgroup.com/en/news/surface-solutions-divestment-22-07-2024.html",
    "https://www.merckgroup.com/en/news/2024/07/22/surface-solutions-divestment.html",
    "https://www.merckgroup.com/en/news/press-releases/2024/07/22/surface-solutions-divestment.html",
    "https://www.merckgroup.com/en/news/surface-solutions-2024.html"
]

for url in urls_to_test:
    try:
        r = requests.head(url, allow_redirects=True, timeout=5)
        print(f"URL: {url} | Status: {r.status_code} | Final: {r.url}")
    except Exception as e:
        print(f"URL: {url} | Error: {e}")
