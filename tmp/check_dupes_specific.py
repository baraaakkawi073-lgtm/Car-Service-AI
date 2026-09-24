import collections, json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
def key(s): return ''.join(c for c in s.casefold() if c.isalnum())
m = json.loads(Path('vehicle-images-manifest.json').read_text(encoding='utf-8'))
hashes = collections.defaultdict(list)
for b, r in m['brands'].items():
    for mod, p in (r.get('models') or {}).items():
        if p.get('status') == 'downloaded':
            hashes[p['sha256']].append((b, mod))
targets = {('Ferrari', 'La Ferrari'), ('Volvo', 'VNL')}
for h, v in hashes.items():
    if len(v) > 1 and any(t in targets for t in v):
        print('sha', h[:10], '->', v)