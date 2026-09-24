import json, sys, hashlib
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
def key(s): return ''.join(c for c in s.casefold() if c.isalnum())
m = json.loads(Path('vehicle-images-manifest.json').read_text(encoding='utf-8'))
for group in [['Bugatti','BUGATTI'], ['Daewoo','DAEWOO'], ['Lotus','LOTUS']]:
    for b in group:
        rec = m['brands'].get(b, {}).get('models', {})
        print('==', b, 'models:', len(rec))
        for mod, p in list(rec.items())[:6]:
            print('   ', mod, '->', p.get('status'), (p.get('path') or '').split('/')[-1])
            if p.get('status') == 'downloaded':
                fp = Path((p.get('path') or '').lstrip('/'))
                if fp.exists():
                    d = hashlib.sha256(fp.read_bytes()).hexdigest()
                    print('       record_sha=', p['sha256'][:12], 'disk_sha=', d[:12], 'MATCH' if p['sha256']==d else 'STALE')
    print()