"""Regenerate vehicle_assets.js from the FULL manifest (all brands).

Unlike finalize_vehicle_assets.py this does NOT rewrite config.py MANUFACTURERS:
the 342 truck/bus/specialty brands stay out of the wizard's selectable picker.
It only broadens the frontend asset map so any make/model that is looked up
(e.g. via the live NHTSA catalogue) can resolve to a shipped photo.

Same verification rules as the audit:
  * only status='downloaded' with a present local file
  * sha256 duplicates across model names are dropped (ambiguous dupe)
"""
import collections
import hashlib
import html
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def key(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s).casefold() if c.isalnum())

def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))

manifest = read('vehicle-images-manifest.json')
logos = {}
images = {}
credits = []
ambiguous = []
hashes = collections.defaultdict(list)
for brand, record in manifest['brands'].items():
    logo = record.get('logo') or ''
    if logo and (ROOT / logo.lstrip('/')).is_file():
        logos[key(brand)] = logo
    images[key(brand)] = {}
    for model, photo in (record.get('models') or {}).items():
        path = photo.get('path') or ''
        if photo.get('status') == 'downloaded' and path and (ROOT / path.lstrip('/')).is_file():
            hashes[photo['sha256']].append((brand, model, path))
            images[key(brand)][key(model)] = {k: photo[k] for k in
                ['path', 'attribution', 'license', 'filePage']}
            credits.append({'brand': brand, 'model': model,
                            'attribution': photo.get('attribution', ''),
                            'license': photo.get('license', ''),
                            'licenseUrl': photo.get('licenseUrl', ''),
                            'filePage': photo.get('filePage', ''),
                            'modification': photo.get('modification', '')})
# Same-source photo assigned to multiple model names is not trusted.
for group in hashes.values():
    if len(group) > 1:
        for brand, model, _ in group:
            images[key(brand)].pop(key(model), None)
            ambiguous.append({'brand': brand, 'model': model})

def escape(v):
    return html.escape(v, quote=True)

body = ['<!doctype html><html lang="en"><meta charset="utf-8"><title>Vehicle photo credits</title><h1>Vehicle photo credits</h1>']
for c in sorted(credits, key=lambda x: (x['brand'].lower(), x['model'].lower())):
    body.append('<article><h2>' + escape(c['brand'] + ' ' + c['model']) + '</h2><p>'
        + escape(c['attribution']) + ' — <a href="' + escape(c['licenseUrl']) + '">'
        + escape(c['license']) + '</a> — <a href="' + escape(c['filePage']) + '">Source photograph</a>. '
        + escape(c['modification']) + '</p></article>')
body.append('</html>')
(ROOT / 'image/vehicles/credits.html').write_text('\n'.join(body), encoding='utf-8')

asset_data = {'logos': logos, 'images': images}
out = ROOT / 'src/ai_report/static/vehicle_assets.js'
out.write_text(
    '// Generated from vehicle-images-manifest.json. Only audited local assets.\n'
    'window.CSAI_VEHICLE_ASSETS = ' + json.dumps(asset_data, ensure_ascii=False, separators=(',', ':')) + ';\n',
    encoding='utf-8')

brands_with_images = sum(1 for v in images.values() if v)
models_with_images = sum(len(v) for v in images.values())
print(json.dumps({
    'brands_with_logos': len(logos),
    'brands_with_images': brands_with_images,
    'models_with_images': models_with_images,
    'credits_written': len(credits),
    'ambiguous_duplicates_dropped': len(ambiguous),
}, indent=2))
print('wrote', out.name, out.stat().st_size, 'bytes')