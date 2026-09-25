import hashlib
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'vehicle-images-manifest.json').read_text(encoding='utf-8'))

groups = {}
count = 0
missing = []
for bb, bd in manifest['brands'].items():
    for mm, mmd in bd.get('models', {}).items():
        count += 1
        if not isinstance(mmd, dict) or 'path' not in mmd or not mmd['path']:
            missing.append((bb, mm, '<no path>'))
            continue
        p = ROOT / mmd['path'].lstrip('/')
        if not p.exists():
            missing.append((bb, mm, mmd['path']))
            continue
        d = hashlib.sha256(p.read_bytes()).hexdigest()
        groups.setdefault(d, []).append((bb, mm, mmd['path']))

dups = {d: v for d, v in groups.items() if len(v) > 1}
print(f'total={count} missing={len(missing)} dup_groups={len(dups)} dup_members={sum(len(v)-1 for v in dups.values())}')
for d, members in sorted(dups.items(), key=lambda kv: -len(kv[1])):
    print(f'\n[{d[:12]}]')
    for bb, mm, path in members:
        print(f'   {bb} :: {mm}  ->  {path}')
print('\nMISSING FILES:')
for m in missing:
    print('  ', m)