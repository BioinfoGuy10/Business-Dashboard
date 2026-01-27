import requests

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
base = "https://www.merckgroup.com/en"
paths = [
    "/news",
    "/news/press-releases",
    "/media/press-releases",
    "/newsroom",
    "/company/news",
    "/news-and-media",
    "/media/news-releases"
]

for p in paths:
    url = base + p + ".html"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"{url}: {r.status_code}")
    except:
        print(f"{url}: failed")
