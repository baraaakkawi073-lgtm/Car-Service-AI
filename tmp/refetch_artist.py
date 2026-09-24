import json, sys
sys.stdout.reconfigure(encoding='utf-8')

# File pages that had empty attribution
cases = [
    ('SEAGRAVE', 'Aerial', 'File:Seagrave 85\' Aerial ladder truck - DPLA - 63bd49726f5c45174f245239151aaa9c.jpg'),
    ('SEAGRAVE', 'Ladder', 'File:Seagrave 85\' Aerial ladder truck - DPLA - 63bd49726f5c45174f245239151aaa9c.jpg'),
    ('Maserati', 'Coupe', 'File:Maserati Coupe vl blue.jpg'),
]

lic_map = {}
title = "$1"
import urllib.parse, urllib.request
UA = {'User-Agent': 'CarServiceAI/1.1 (https://github.com/anomalyco/opencode; vehicle photo lookup for a car-maintenance assistant) python-httpx/0.27'}

for brand, model, title in cases:
    # strip File: prefix spaces
    canonical = title[5:].replace(' ', '_')
    url = ('https://commons.wikimedia.org/w/api.php?action=query&titles=File:'
           + urllib.parse.quote(canonical)
           + '&prop=imageinfo&iiprop=extmetadata&format=json')
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            page = next(iter(json.load(r)['query']['pages'].values()))
        em = page.get('imageinfo', [{}])[0].get('extmetadata', {})
        artist = em.get('Artist', {}).get('value', '')
        import re
        clean = re.sub(r'<[^>]+>', '', artist).strip()
        lic = em.get('LicenseShortName', {}).get('value', '')
        print(brand, model, '| Artist:', clean[:80] or '(none)', '| License:', lic)
        lic_map[brand] = (clean, lic)
    except Exception as e:
        print(brand, model, 'ERROR', e)