import requests, re
headers = {'User-Agent': 'Mozilla/5.0'}
url = "https://www.eqs-news.com/news/corporate?search=Merck"
try:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    links = re.findall('href="(.*?)"', r.text)
    for l in links:
        if 'merck' in l.lower() and '2024' in l:
            print(f"https://www.eqs-news.com{l}")
except Exception as e:
    print(f"Error: {e}")
