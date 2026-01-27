import requests, re
headers = {'User-Agent': 'Mozilla/5.0'}
try:
    r = requests.get('https://www.merckgroup.com/en/news.html', headers=headers, timeout=10)
    links = re.findall('href="(/en/news/.*?\.html)"', r.text)
    for l in sorted(set(links)):
        print(l)
except Exception as e:
    print(f"Error: {e}")
