import hashlib
import html
import io
import json
import re
import sys
from pathlib import Path

import requests
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
HEADERS = {'User-Agent': 'CarServiceAI/1.2 (vehicle duplicate fix) python-requests/2.31'}
CLIENT = requests.Session()
CLIENT.headers.update(HEADERS)
COMMONS = 'https://commons.wikimedia.org/w/api.php'


def get(**params):
    r = CLIENT.get(COMMONS, params=params, timeout=40)
    return r


def clean(v):
    return html.unescape(re.sub('<[^>]+>', '', str(v or ''))).strip()


def do_fix():
    manifest = json.loads((ROOT / 'vehicle-images-manifest.json').read_text(encoding='utf-8'))
    assets_js = (ROOT / 'src/ai_report/static/vehicle_assets.js').read_text(encoding='utf-8')
    assets = json.loads(assets_js.split(' = ', 1)[1].rstrip(';\n'))

    # find director record
    rec = None
    for bb, bd in manifest['brands'].items():
        if ''.join(c for c in bb.casefold() if c.isalnum()) == 'chanje':
            rec = bd['models']['Chanje Truck']
            brand_name = bb
            break
    if rec is None:
        print('chanje truck record not found')
        return
    path = rec['path']
    dest = ROOT / path.lstrip('/')

    # used source pages from all connected models (prevent visual dup)
    used_fp = set()
    for bd in manifest['brands'].values():
        for m, r in bd.get('models', {}).items():
            if r and r.get('filePage'):
                used_fp.add(r['filePage'])

    candidates = [
        'File:Yangtse WG5031XXYBEV Electric Delivery Van front 8.16.18.jpg',
        'File:Changjiang EV Yisheng 001.jpg',
    ]
    chosen = None
    for title in candidates:
        r = get(action='query', format='json', prop='imageinfo',
                iiprop='url|mime|size|extmetadata', iiurlwidth='960', titles=title)
        for p in (r.json().get('query', {}).get('pages', {}) or {}).values():
            ii = (p.get('imageinfo') or [{}])[0]
            em = ii.get('extmetadata', {})
            fields = {k: clean(v.get('value', '')) for k, v in em.items()}
            lic = fields.get('LicenseShortName', '')
            if not (lic.startswith('CC BY') or lic.startswith('CC0') or 'Public domain' in lic):
                print('license reject', title, lic)
                continue
            if ii.get('mime') != 'image/jpeg':
                print('mime reject', title)
                continue
            page = ii.get('descriptionurl', '')
            if page in used_fp:
                print('page already used by another model:', page)
                continue
            img = Image.open(io.BytesIO(CLIENT.get(ii['thumburl'], timeout=40).content))
            img.thumbnail((640, 440))
            img = img.convert('RGB')
            data = None
            for q in (75, 65, 55):
                buf = io.BytesIO()
                img.save(buf, 'WEBP', quality=q, method=6)
                data = buf.getvalue()
                if len(data) < 250_000:
                    break
            if data is None or len(data) >= 250_000:
                print('too large', title)
                continue
            d = hashlib.sha256(data).hexdigest()
            dest.write_bytes(data)
            chosen = {
                'title': title, 'digest': d, 'fields': fields, 'lic': lic,
                'thumb': ii['thumburl'], 'page': page,
            }
            break
        if chosen:
            break

    if not chosen:
        print('no candidate accepted')
        return

    rec.update({
        'sourceType': 'wikimedia_commons',
        'imageSource': 'Wikimedia Commons',
        'status': 'downloaded',
        'sourceUrl': chosen['thumb'],
        'sourcePage': chosen['page'],
        'attribution': chosen['fields'].get('Artist', ''),
        'license': chosen['lic'],
        'licenseUrl': chosen['fields'].get('LicenseUrl', ''),
        'description': chosen['fields'].get('ImageDescription', ''),
        'filePage': chosen['page'],
        'modification': 'Resized to at most 640\u00d7440 and converted to WebP',
        'sha256': chosen['digest'],
    })
    assets['images']['chanje']['chanjetruck'] = {
        'path': path,
        'attribution': chosen['fields'].get('Artist', ''),
        'license': chosen['lic'],
        'filePage': chosen['page'],
    }
    (ROOT / 'vehicle-images-manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'src/ai_report/static/vehicle_assets.js').write_text(
        '// Generated from vehicle-images-manifest.json. Only audited local assets.\n'
        'window.CSAI_VEHICLE_ASSETS = ' + json.dumps(assets, ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')
    print('OK CHANJE::Chanje Truck <-', chosen['title'], chosen['digest'][:12])


if __name__ == '__main__':
    do_fix()