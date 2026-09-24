import json, sys, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
UA = {'User-Agent': 'CarServiceAI/1.1 (https://github.com/anomalyco/opencode; vehicle photo lookup) python-httpx/0.27'}
for t in ['File:Maserati Coupe vl blue.jpg',
          "File:Seagrave 85' Aerial ladder truck - DPLA - 63bd49726f5c45174f245239151aaa9c.jpg",
          'File:Nd vs usc defense 2005.JPG',
          'File:Le Galant tailleur - film de Mack Sennett - scénario - btv1b64089786.jpg',
          'File:Amulet depicting the double feather crown, gabbro - Museo Egizio, Turin C 1297 ND p02.jpg']:
    url = ('https://commons.wikimedia.org/w/api.php?action=query&titles='
           + urllib.parse.quote(t.replace(' ', '_'))
           + '&prop=imageinfo&iiprop=extmetadata&format=json')
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        page = next(iter(json.load(r)['query']['pages'].values()))
    em = page.get('imageinfo', [{}])[0].get('extmetadata', {})
    artist = em.get('Artist', {}).get('value', '')
    import re
    clean = re.sub(r'<[^>]+>', '', artist).strip()
    print('==', t)
    print('  Artist:', repr(clean)[:160])
    print('  Categories:', repr(em.get('Categories', {}).get('value', ''))[:160])
    print('  License:', em.get('LicenseShortName', {}).get('value', ''))