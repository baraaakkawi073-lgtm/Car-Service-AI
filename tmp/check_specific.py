import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
def key(s): return ''.join(c for c in s.casefold() if c.isalnum())
m = json.loads(Path('vehicle-images-manifest.json').read_text(encoding='utf-8'))
for b, model in [('Ferrari', 'La Ferrari'), ('Volvo', 'VNL')]:
    rec = m['brands'].get(b, {}).get('models', {}).get(model)
    print(b, '|', model, '->', rec.get('status'), rec.get('path'), rec.get('reason', '') if rec else 'NO RECORD')
# show which ferarri/volvo entries downloaded
for b in ('Ferrari', 'Volvo'):
    dl = [(mo, p.get('path')) for mo, p in m['brands'].get(b, {}).get('models', {}).items() if p.get('status') == 'downloaded']
    print(b, 'downloaded count:', len(dl), dl[:6])