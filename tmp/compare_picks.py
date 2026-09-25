import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
cur = json.load(open('vehicle-images-manifest.json', encoding='utf-8'))
head = json.loads(__import__('subprocess').check_output(
    ['git', 'show', 'HEAD:vehicle-images-manifest.json'], encoding='utf-8'))

targets = [
    ('FALCON', 'Model 1'), ('FALCON', 'Model 3'), ('FALCON', 'Model 6'), ('FALCON', 'Model 9'),
    ('KALMAR', 'Model 30'), ('KALMAR', 'Model 50'),
    ('VOLVO', 'Cab Over Engine HT'), ('VOLVO', 'Cab Over Engine LT'), ('VOLVO', 'VN (4)'),
    ('BYD', 'Electric Truck Chassis'), ('BYD', 'Electric Truck'), ('BYD', 'Shark'),
    ('FRONTLINE', 'Defense - Light'), ('FRONTLINE', 'Defense - Medium'), ('FRONTLINE', 'Defense - Heavy'),
    ('FRONTLINE', 'Aerial'),
]
for brand, model in targets:
    h = head.get('brands', {}).get(brand, {}).get('models', {}).get(model)
    c = cur.get('brands', {}).get(brand, {}).get('models', {}).get(model)
    print('\n###', brand, '::', model)
    if h:
        print('  HEAD filePage:', h.get('filePage'))
        print('  HEAD desc    :', str(h.get('description', ''))[:160])
    else:
        print('  HEAD: (none)')
    if c:
        print('  CUR  filePage:', c.get('filePage'))
        print('  CUR  desc    :', str(c.get('description', ''))[:160])
    else:
        print('  CUR: (none)')