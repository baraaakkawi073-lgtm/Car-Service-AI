import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
m = json.loads((ROOT / 'vehicle-images-manifest.json').read_text(encoding='utf-8'))

missing_specs = {
    ('MACK', 'LE'): 'No matching Commons photograph',
    ('ND', 'Defense - Heavy'): 'No matching Commons photograph',
    ('ND', 'Defense - Light'): 'No matching Commons photograph',
    ('ND', 'Defense - Medium'): 'No matching Commons photograph',
    ('ND', 'Double'): 'No matching Commons photograph',
    ('Maserati', 'Coupe'): 'No machine-readable author, CC BY-SA attribution impossible',
}

def clean(rec):
    for k in ['sourceUrl', 'path', 'sha256', 'attribution', 'license', 'licenseUrl',
              'modelDescription', 'description', 'filePage', 'modification', 'verification',
              'imageSource', 'sourceType', 'sourcePage']:
        rec.pop(k, None)

changes = []
for (b, mod), reason in missing_specs.items():
    rec = m['brands'][b]['models'][mod]
    old = rec.get('status')
    clean(rec)
    rec['status'] = 'missing'
    rec['reason'] = reason
    changes.append((b, mod, old, 'missing'))

# SEAGRAVE photos are legit but need real attribution
for b, mod in [('SEAGRAVE', 'Aerial'), ('SEAGRAVE', 'Ladder')]:
    rec = m['brands'][b]['models'][mod]
    rec['attribution'] = 'Columbus Metropolitan Library'
    changes.append((b, mod, 'downloaded', 'downloaded+attribution'))

# delete files for now-missing records
files = [
    'image/vehicles/mack/le.webp',
    'image/vehicles/nd/defense-heavy.webp',
    'image/vehicles/nd/defense-light.webp',
    'image/vehicles/nd/defense-medium.webp',
    'image/vehicles/nd/double.webp',
    'image/vehicles/maserati/coupe.webp',
    'image/vehicles/nd/defense - heavy.webp',
    'image/vehicles/nd/defense - light.webp',
    'image/vehicles/nd/defense - medium.webp',
]
for f in files:
    p = ROOT / f
    if p.exists():
        p.unlink()
        print('deleted', f)

(ROOT / 'vehicle-images-manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
for c in changes:
    print(c)