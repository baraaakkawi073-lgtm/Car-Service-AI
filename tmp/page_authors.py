import re, sys, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
UA = {'User-Agent': 'CarServiceAI/1.1 (https://github.com/anomalyco/opencode; vehicle photo lookup) python-httpx/0.27'}
urls = [
    'https://commons.wikimedia.org/wiki/File:Maserati_Coupe_vl_blue.jpg',
]
for url in urls:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        html = r.read().decode('utf-8', 'replace')
    for label, pat in [('creator', r'id="creator"[\s\S]{0,1600}'),
                       ('author', r'[Aa]uthor[\s\S]{0,600}'),
                       ('Photographer', r'[Pp]hotographer[\s\S]{0,600}')]:
        m = re.search(pat, html)
        txt = re.sub(r'<[^>]+>', ' ', m.group(0)).strip() if m else '(none)'
        print(label, ':', ' '.join(txt.split())[:220])