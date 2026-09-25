import hashlib
import json
import os
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding='utf-8')


def key(v):
    return ''.join(c for c in unicodedata.normalize('NFKD', v).casefold() if c.isalnum())


ROOT = r'C:\workbench\fast\Car-Service-AI'
assets = json.loads(open(ROOT + r'\src\ai_report\static\vehicle_assets.js', encoding='utf-8').read().split(' = ', 1)[1].rstrip(';\n'))
manifest = json.loads(open(ROOT + r'\vehicle-images-manifest.json', encoding='utf-8').read())

report = {'missing': [], 'size_bad': [], 'dup': [], 'sha_mismatch': [],
          'no_record': [], 'no_attrib': [], 'non_ascii': [], 'stale_refs': []}

seen = {}
n = 0
man_map = {}
for b, data in manifest['brands'].items():
    for m, r in data['models'].items():
        man_map[(key(b), key(m))] = (b, m, r)

for brand, models in assets['images'].items():
    for model, photo in models.items():
        n += 1
        rel = photo['path'].lstrip('/')
        p = os.path.join(ROOT, rel.replace('/', os.sep))
        if not os.path.isfile(p):
            report['missing'].append((brand, model, rel))
            continue
        size = os.path.getsize(p)
        if not (0 < size < 250_000):
            report['size_bad'].append((brand, model, rel, size))
        d = hashlib.sha256(open(p, 'rb').read()).hexdigest()
        if d in seen:
            report['dup'].append((brand, model, d[:12], seen[d]))
        seen[d] = f'{brand}/{model}'
        rec = man_map.get((key(brand), key(model)))
        if rec is None:
            report['no_record'].append((brand, model, rel))
        elif rec[2].get('sha256') != d:
            report['sha_mismatch'].append((brand, model, rel, rec[2].get('sha256', '')[:12], d[:12]))
        if not (photo.get('attribution') and photo.get('license') and photo.get('filePage')):
            report['no_attrib'].append((brand, model))
        if not rel.isascii():
            report['non_ascii'].append((brand, model, rel))

# stale one:1 references anywhere in the static assets
assets_text = open(ROOT + r'\src\ai_report\static\vehicle_assets.js', encoding='utf-8').read()
for pat in ['one:1', 'koenigsegg/one"', 'koenigsegg/one.webp']:
    for m in re.finditer(re.escape(pat), assets_text):
        report['stale_refs'].append(('assets.js', pat))

for label, lst in report.items():
    print(f'== {label}: {len(lst)}')
    for x in lst[:20]:
        print('   ', x)

print('TOTAL CONNECTED:', n)
print('UNIQUE DIGESTS:', len(seen))

# logos check
logos = assets.get('logos', {})
missing_logos = [k for k, v in logos.items() if not os.path.isfile(os.path.join(ROOT, v.lstrip('/').replace('/', os.sep)))]
print('LOGOS:', len(logos), 'MISSING:', missing_logos)