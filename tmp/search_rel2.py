import re
import sys
import time

import requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
H = {'User-Agent': 'CarServiceAI/1.2 (asset verification; local) python-requests/2.31'}
S = requests.Session()
S.headers.update(H)


def search(term, limit=8, retries=6):
    for attempt in range(retries):
        r = S.get('https://commons.wikimedia.org/w/api.php', params={
            'action': 'query', 'generator': 'search', 'gsrsearch': term,
            'gsrnamespace': 6, 'gsrlimit': limit, 'prop': 'imageinfo',
            'iiprop': 'url|size|extmetadata|mime', 'iiurlwidth': 960, 'format': 'json'},
            timeout=30)
        d = r.json()
        if 'error' in d:
            if d['error'].get('code') == 'cirrussearch-too-busy-error':
                time.sleep(2.0)
                continue
            print('  API ERROR', d['error'], file=sys.stderr)
            return []
        pages = d.get('query', {}).get('pages', {})
        out = []
        for p in sorted(pages.values(), key=lambda x: x.get('index', 0)):
            ii = p.get('imageinfo', [{}])[0]
            em = ii.get('extmetadata', {})
            if 'image' not in (ii.get('mime') or ''):
                continue
            w, h = ii.get('width', 0), ii.get('height', 0)
            if w < 300 or h < 200:
                continue
            lic = em.get('LicenseShortName', {}).get('value', '')
            out.append((p['title'], ii.get('thumburl'), w, h, lic,
                        re.sub(r'<[^>]+>', '', em.get('ImageDescription', {}).get('value', ''))[:160]))
        return out


queries = [
    ('KALMAR::Model 50', 'Kalmar forklift truck', 6),
    ('KALMAR::Model 50 alt', 'Kalmar terminal tractor', 6),
    ('ND::RT-1950', 'white garbage truck Reutlingen', 4),
    ('ND::RT-2600', 'Volvo truck Reutlingen', 4),
    ('ND::RT-3300', 'Mercedes truck Reutlingen', 4),
    ('ND::RT series alt', 'terminal tractor truck', 5),
    ('FRONTLINE::Defense L/M', 'military tactical vehicle army truck', 6),
    ('FRONTLINE::Defense alt', 'mine resistant ambush protected vehicle', 4),
    ('VOLVO::COE HT', 'Volvo FH truck side', 6),
    ('VOLVO::COE HT alt', 'Volvo F12 truck', 6),
    ('BYD::ETC', 'BYD T8 electric truck', 5),
]
for label, q, n in queries:
    print('\n###', label, '::', q)
    try:
        for t in search(q, n):
            print('  -', t[0], '|', t[3], 'x', t[2], '|', t[4], '|', t[5][:110])
    except Exception as e:
        print('   ERROR', e)
    time.sleep(0.5)