import requests

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
base = "https://www.merckgroup.com/en/news/"
candidates = [
    "2024/07/25/surface-solutions-divestment.html",
    "2024/07/25/surface-solutions.html",
    "surface-solutions-25-07-2024.html",
    "surface-solutions-divestment-25-07-2024.html",
    "merck-signs-agreement-to-sell-surface-solutions-business-unit-to-gnmi-25-07-2024.html",
    "press-releases/2024/07/25/surface-solutions.html",
    "2024/07/25/merck-signs-agreement-to-sell-surface-solutions-business-unit-to-gnmi.html"
]

for c in candidates:
    url = base + c
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"{url}: {r.status_code}")
        if r.status_code == 200:
            print(f"!!! FOUND IT: {url}")
            break
    except Exception as e:
        print(f"{url}: FAILED - {e}")
