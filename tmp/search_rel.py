import json
import re
import sys
import time

import requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HEADERS = {'User-Agent': 'CarServiceAI/1.2 (asset verification; local) python-requests/2.31'}
S = requests.Session()
S.headers.update(HEADERS)


def search(term, limit=8):
    r = S.get('https://commons.wikimedia.org/w/api.php', params={
        'action': 'query', 'generator': 'search', 'gsrsearch': term,
        'gsrnamespace': 6, 'gsrlimit': limit, 'prop': 'imageinfo',
        'iiprop': 'url|size|extmetadata', 'iiurlwidth': 960, 'format': 'json'}, timeout=30)
    pages = r.json().get('query', {}).get('pages', {})
    out = []
    for p in sorted(pages.values(), key=lambda x: x.get('index', 0)):
        ii = p.get('imageinfo', [{}])[0]
        em = ii.get('extmetadata', {})
        mime = ii.get('mime', '')
        if 'image' not in (mime or ''):
            continue
        w, h = ii.get('width', 0), ii.get('height', 0)
        if w < 200 or h < 150:
            continue
        out.append({
            'title': p['title'],
            'thumb': ii.get('thumburl'),
            'w': w, 'h': h,
            'license': em.get('LicenseShortName', {}).get('value', ''),
            'desc': re.sub(r'<[^>]+>', '', em.get('ImageDescription', {}).get('value', ''))[:180],
        })
    return out


queries = [
    ('KALMAR Model 50', 'Kalmar terminal tractor', 6),
    ('KALMAR Model 50 (alt)', 'Kalmar Ottawa terminal tractor', 6),
    ('FRONTLINE Defense Light', 'Frontline armored vehicle', 6),
    ('FRONTLINE Defense (alt)', 'Frontline military vehicle', 6),
    ('BYD Electric Truck Chassis', 'BYD T8 electric truck', 6),
    ('BYD Electric Truck Chassis (alt)', 'BYD electric truck', 6),
    ('VOLVO Cab Over Engine HT', 'Volvo VNL highway truck', 5),
    ('FALCON Model 9', 'Falcon 9 rocket transport', 4),
    ('KALMAR Model 50 (forklift)', 'Kalmar reach stacker', 6),
]
for label, q, n in queries:
    print('\n###', label, '::', q)
    try:
        for r in search(q, n):
            print('  -', r['title'])
            print('     ', r['w'], 'x', r['h'], '|', r['license'], '|', r['desc'][:120])
    except Exception as e:
        print('   ERROR', e)
    time.sleep(0.3)