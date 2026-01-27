import requests, re
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
url = "https://www.merckgroup.com/en/news/press-releases/2024.html"
try:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    links = re.findall('href="(.*?)"', r.text)
    for l in links:
        if '2024/' in l:
            print(l)
except Exception as e:
    print(f"Error: {e}")
