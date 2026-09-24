import json, random, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
m = json.loads(Path('vehicle-images-manifest.json').read_text(encoding='utf-8'))
recs = []
for b, r in m['brands'].items():
    for mod, p in (r.get('models') or {}).items():
        if p.get('status') == 'downloaded':
            recs.append((b, mod, p))
random.seed(7)
for b, mod, p in random.sample(recs, 6):
    print(f"{b} | {mod}")
    print('   license:', p.get('license'), '| artist:', (p.get('attribution') or '')[:60])
    print('   filePage:', p.get('filePage'))
    print('   licenseUrl:', p.get('licenseUrl'))