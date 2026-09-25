import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

source = (ROOT / 'src/ai_report/static/vehicle_assets.js').read_text(encoding='utf-8')
assets = json.loads(source.split(' = ', 1)[1].rstrip(';\n'))
manifest = json.loads((ROOT / 'vehicle-images-manifest.json').read_text(encoding='utf-8'))

digest_to_models = {}
line = '=' * 100
print(line)
print('CONNECTED ASSETS: %d models, %d brands' % (
    sum(len(m) for m in assets['images'].values()), len(assets['images'])))
print(line)

for brand in assets['images']:
    for model, photo in assets['images'][brand].items():
        rel = photo['path'].lstrip('/')
        path = ROOT / rel
        if not path.is_file():
            print('MISSING FILE: %s %s -> %s' % (brand, model, photo['path']))
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        digest_to_models.setdefault(digest, []).append((brand, model, photo['path']))

dupes = {d: v for d, v in digest_to_models.items() if len(v) > 1}
print('DUPLICATE DIGEST GROUPS: %d' % len(dupes))
print(line)

for digest, entries in sorted(dupes.items()):
    print('DIGEST %s  (n=%d)' % (digest, len(entries)))
    for brand, model, path in entries:
        rec = None
        for b, data in manifest['brands'].items():
            if b.lower().replace(' ', '') == brand.lower().replace(' ', ''):
                for m, r in data['models'].items():
                    if m.lower().replace(' ', '') == model.lower().replace(' ', ''):
                        rec = r
                        break
        su = rec.get('sourceUrl') if rec else None
        sp = rec.get('sourcePage') if rec else None
        print('  %s / %s -> %s' % (brand, model, path))
        print('     sourceUrl : %s' % (su or '-'))
        print('     sourcePage: %s' % (sp or '-'))
    print('-' * 80)