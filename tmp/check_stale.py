import json, sys, hashlib
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
m = json.loads(Path('vehicle-images-manifest.json').read_text(encoding='utf-8'))
stale = []
for b, r in m['brands'].items():
    for mod, p in (r.get('models') or {}).items():
        if p.get('status') != 'downloaded':
            continue
        fp = Path((p.get('path') or '').lstrip('/'))
        if not fp.exists():
            stale.append((b, mod, 'MISSING FILE'))
        else:
            d = hashlib.sha256(fp.read_bytes()).hexdigest()
            if p.get('sha256') != d:
                stale.append((b, mod, p.get('sha256', '')[:12], d[:12]))
print('stale/missing downloaded records:', len(stale))
for row in stale:
    print('  ', row)