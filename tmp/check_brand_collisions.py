import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
def key(s): return ''.join(c for c in s.casefold() if c.isalnum())
m = json.loads(Path('vehicle-images-manifest.json').read_text(encoding='utf-8'))
brands = m['brands']
groups = {}
for b in brands:
    groups.setdefault(key(b), []).append(b)
dups = {k: v for k, v in groups.items() if len(v) > 1}
print('case-collision brand groups:', len(dups))
for k, v in sorted(dups.items()):
    haslogo = [b for b in v if brands[b].get('logo')]
    print('  ', key(v[0]), '->', v, '| logo:', haslogo)