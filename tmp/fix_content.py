import hashlib
import io
import json
import re
import sys
import time

import requests
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = r'C:\workbench\fast\Car-Service-AI'
H = {'User-Agent': 'CarServiceAI/1.2 (asset repair; local) python-requests/2.31'}
S = requests.Session()
S.headers.update(H)


def api(**params):
    params.setdefault('format', 'json')
    params.setdefault('action', 'query')
    for attempt in range(8):
        r = S.get('https://commons.wikimedia.org/w/api.php', params=params, timeout=30)
        d = r.json()
        if 'error' not in d:
            return d
        if d['error'].get('code') == 'cirrussearch-too-busy-error':
            time.sleep(2.5)
            continue
        raise RuntimeError(d['error'])
    raise RuntimeError('search too busy')


def find(title):
    d = api(titles=title, prop='imageinfo', iiprop='url|size|mime|extmetadata', iiurlwidth=1200)
    p = next(iter(d['query']['pages'].values()))
    return p.get('imageinfo', [None])[0]


targets = {
    ('KALMAR', 'Model 50'): ['File:Sisu Ottawa terminal tractor, front right.jpg'],
    ('FRONTLINE', 'Defense - Light'): ['File:US Army Truck.jpg'],
    ('FRONTLINE', 'Defense - Medium'): ["File:Medium tactical vehicle - PROLOG '85 -2.JPEG"],
    ('ND', 'RT - 1950'): ['File:2014 terminal tractor Terberg YT 182.jpg'],
    ('ND', 'RT - 2600'): ['File:Volvo FH 16 8x4 2014. Spielvogel 3.JPG'],
    ('ND', 'RT - 3300'): ['File:6-365 Volvo FH.jpg'],
    ('Volvo', 'Cab Over Engine HT'): ['File:Volvo FH 16 8x4 2014. Spielvogel 5.JPG',
                                      'File:Red Volvo FH with Stobart trailer on the M4 M6, Clonard, Co. Meath, 2 January 2014.jpg'],
    ('BYD', 'Electric Truck Chassis'): ['File:BYD T8SA.jpg', 'File:BYD C9 electric coach. Spielvogel.jpg'],
}

manifest = json.load(open(ROOT + r'\vehicle-images-manifest.json', encoding='utf-8'))
used_pages = set()
for b, data in manifest['brands'].items():
    for m, r in data['models'].items():
        used_pages.add((r.get('sourcePage') or '').rsplit('/', 1)[-1])


def pick(brand, model):
    rec = manifest['brands'][brand]['models'][model]
    old = ROOT + '\\' + rec['path'].lstrip('/').replace('/', '\\')
    for title in targets.get((brand, model), []):
        ii = find(title)
        if ii is None:
            print(f'  no imageinfo: {title}')
            continue
        if 'image' not in (ii.get('mime') or ''):
            print(f'  not an image: {title}')
            continue
        em = ii.get('extmetadata', {})
        lic = em.get('LicenseShortName', {}).get('value', '')
        if not (lic.startswith('CC') or lic in ('Public domain', 'PD')):
            print(f'  license not CC/PD: {title} -> {lic}')
            continue
        fname = title.rsplit('/', 1)[-1]
        if fname in used_pages:
            print(f'  page already used: {title}')
            continue
        w, h = ii.get('width', 0), ii.get('height', 0)
        scale = min(640.0 / w, 440.0 / h, 1.0)
        tw, th = max(1, round(w * scale)), max(1, round(h * scale))
        data = None
        for q in (75, 65, 55):
            img = Image.open(io.BytesIO(S.get(ii['thumburl'], timeout=60).content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img = img.resize((tw, th), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, 'WEBP', quality=q, method=6)
            blob = buf.getvalue()
            if len(blob) < 250_000:
                data = blob
                break
        if data is None:
            print(f'  still too large: {title}')
            continue
        digest = hashlib.sha256(data).hexdigest()
        others = set()
        for b, data2 in json.loads(open(ROOT + r'\src\ai_report\static\vehicle_assets.js', encoding='utf-8')
                                   .read().split(' = ', 1)[1].rstrip(';\n').lstrip('\ufeff'))['images'].items():
            for m, ph in data2.items():
                fp = ROOT + '\\' + ph['path'].lstrip('/').replace('/', '\\')
                try:
                    others.add(hashlib.sha256(open(fp, 'rb').read()).hexdigest())
                except OSError:
                    pass
        if digest in others:
            print(f'  digest clash: {title}')
            continue
        open(old, 'wb').write(data)
        page_url = 'https://commons.wikimedia.org/wiki/' + title.replace(' ', '_')
        rec['path'] = '/' + rec['path'].lstrip('/')
        rec['sourcePage'] = page_url
        rec['filePage'] = page_url
        rec['sourceUrl'] = ii.get('thumburl', '')
        rec['attribution'] = re.sub(r'<[^>]+>', '', em.get('Artist', {}).get('value', ''))[:300] or ''
        rec['license'] = lic or ''
        rec['licenseUrl'] = em.get('LicenseUrl', {}).get('value', '')
        desc = re.sub(r'<[^>]+>', '', em.get('ImageDescription', {}).get('value', ''))[:500]
        rec['description'] = desc
        rec['sha256'] = digest
        rec['modification'] = 'Resized to at most 640x440 and converted to WebP'
        rec['verifiedModel'] = True
        used_pages.add(fname)
        print(f'  OK {title} sha={digest[:12]}')
        return True
    print('  NO CANDIDATE WORKED')
    return False


ok = 0
for (brand, model) in targets:
    print('###', brand, '::', model)
    if pick(brand, model):
        ok += 1
    time.sleep(0.5)

json.dump(manifest, open(ROOT + r'\vehicle-images-manifest.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\nreplaced {ok}/{len(targets)}')