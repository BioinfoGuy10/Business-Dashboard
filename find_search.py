import requests, re
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
url = "https://www.merckgroup.com/en/news.html"
try:
    r = requests.get(url, headers=headers, timeout=10)
    # Look for search forms or inputs
    matches = re.findall('(<form[^>]*?>)', r.text)
    for m in matches:
        print(m)
    matches = re.findall('(<input[^>]*?>)', r.text)
    for m in matches:
        if 'search' in m.lower():
            print(m)
except Exception as e:
    print(f"Error: {e}")
