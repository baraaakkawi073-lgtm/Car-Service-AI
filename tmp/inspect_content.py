import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
m = json.load(open('vehicle-images-manifest.json', encoding='utf-8'))
for bn in ['FALCON', 'KALMAR', 'FRONTLINE', 'VOLVO', 'OSHKOSH', 'TERN', 'ND',
           'INTERNATIONAL', 'WHITE', 'ORION BUS', 'HYUNDAI', 'GMC', 'PETERBILT', 'BYD']:
    b = m['brands'].get(bn)
    if not b:
        continue
    print('==', bn)
    for mm, r in b.get('models', {}).items():
        if not isinstance(r, dict) or not r.get('path'):
            continue
        print('  ', mm, '|', (r.get('sourcePage') or '')[:110])
        print('      desc:', (r.get('description') or '')[:80])