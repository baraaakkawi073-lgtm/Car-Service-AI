import httpx, requests, sys
sys.stdout.reconfigure(encoding='utf-8')
url = 'https://commons.wikimedia.org/w/api.php'
params = {'action': 'query', 'format': 'json', 'generator': 'search',
          'gsrsearch': 'intitle:"BMW" intitle:"650i" filetype:bitmap',
          'gsrnamespace': '6', 'gsrlimit': '10',
          'prop': 'imageinfo', 'iiprop': 'url|mime|size', 'iiurlwidth': '960'}

uas = ['CarServiceAI-fix/1.0 (test)',
       'CarServiceAI/1.1 (https://github.com/anomalyco/opencode; vehicle photo lookup for a car-maintenance assistant) python-httpx/0.27',
       'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36']
for ua in uas:
    try:
        r = requests.get(url, params=params, headers={'User-Agent': ua}, timeout=30)
        print('REQUESTS', ua[:40], '->', r.status_code)
        if r.status_code == 200:
            d = r.json()
            print('   pages:', len((d.get('query', {}).get('pages') or {})))
        else:
            print('   body s100:', r.text[:120].replace('\n', ' '))
    except Exception as e:
        print('REQUESTS', ua[:40], 'EXC', type(e).__name__, e)
    try:
        c = httpx.Client(headers={'User-Agent': ua}, timeout=30, follow_redirects=True)
        r2 = c.get(url, params=params)
        print('HTTPX   ', ua[:40], '->', r2.status_code)
    except Exception as e:
        print('HTTPX   ', ua[:40], 'EXC', type(e).__name__, e)