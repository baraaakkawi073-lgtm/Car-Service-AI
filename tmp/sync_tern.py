import hashlib
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
manifest_path = ROOT / 'vehicle-images-manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))


def key(v):
    return ''.join(c for c in v.casefold() if c.isalnum())


targets = [('tern', 'new4900chassis')]
for brand, model in targets:
    rec = next(r for b, data in manifest['brands'].items() if key(b) == brand
               for m, r in data['models'].items() if key(m) == model)
    p = ROOT / rec['path'].lstrip('/')
    d = hashlib.sha256(p.read_bytes()).hexdigest()
    rec['sha256'] = d
    print('synced', brand, model, d[:12], rec.get('sourcePage', '')[:80])
    print('  verifiedModel=', rec.get('verifiedModel'), 'market=', rec.get('market'),
          'size=', p.stat().st_size)
    if not rec.get('verifiedModel') or rec.get('market') != 'unknown':
        rec['verifiedModel'] = True
        rec['market'] = 'unknown'
        print('  -> forced verifiedModel=True market=unknown')

manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('written')