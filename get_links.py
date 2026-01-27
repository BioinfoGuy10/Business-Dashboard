import requests, re
headers = {'User-Agent': 'Mozilla/5.0'}
try:
    r = requests.get('https://www.merckgroup.com/en', headers=headers, timeout=10)
    links = re.findall('href="(.*?)"', r.text)
    for l in set(links):
        if 'news' in l or 'press' in l or 'media' in l:
            print(l)
except Exception as e:
    print(f"Error: {e}")
