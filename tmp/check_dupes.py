import collections, json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
def key(s): return ''.join(c for c in s.casefold() if c.isalnum())
m = json.loads(Path('vehicle-images-manifest.json').read_text(encoding='utf-8'))
hashes = collections.defaultdict(list)
for b, r in m['brands'].items():
    for mod, p in (r.get('models') or {}).items():
        if p.get('status') == 'downloaded':
            hashes[p['sha256']].append((b, mod, (p.get('path') or '').split('/')[-1]))
groups = {h: v for h, v in hashes.items() if len(v) > 1}
print('distinct duplicate photo groups:', len(groups))
print('total records in duplicate groups:', sum(len(v) for v in groups.values()))
for h, v in list(groups.items())[:20]:
    names = [f'{b}/{mod}' for b, mod, _ in v]
    print('  sha', h[:10], '->', names)