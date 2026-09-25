import hashlib
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
assets = json.loads((ROOT / 'src/ai_report/static/vehicle_assets.js').read_text(encoding='utf-8')
                     .split(' = ', 1)[1].rstrip(';\n'))
manifest = json.loads((ROOT / 'vehicle-images-manifest.json').read_text(encoding='utf-8'))


def key(v):
    return ''.join(c for c in v.casefold() if c.isalnum())


mismatch = []
for brand, models in assets['images'].items():
    for model, photo in models.items():
        p = ROOT / photo['path'].lstrip('/')
        d = hashlib.sha256(p.read_bytes()).hexdigest()
        rec = next((r for b, data in manifest['brands'].items() if key(b) == brand
                    for m, r in data['models'].items() if key(m) == model), None)
        if rec is None:
            mismatch.append((brand, model, 'NO RECORD'))
        elif rec.get('sha256') != d:
            mismatch.append((brand, model, rec.get('sha256', '')[:12], d[:12],
                             photo['path'], rec.get('sourcePage', '')[:80]))

print(f'mismatches: {len(mismatch)}')
seen = set()
dups = []
for brand, models in assets['images'].items():
    for model, photo in models.items():
        d = hashlib.sha256((ROOT / photo['path'].lstrip('/')).read_bytes()).hexdigest()
        if d in seen:
            dups.append((brand, model, d[:12]))
        seen.add(d)
print(f'duplicate digests: {len(dups)}')
for x in mismatch:
    print('  ', x)
for x in dups:
    print('  DUP', x)