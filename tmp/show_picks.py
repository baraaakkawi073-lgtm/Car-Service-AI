import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
m = json.load(open('vehicle-images-manifest.json', encoding='utf-8'))
checks = []
for brand, data in m['brands'].items() or []:
    pass
targets = {
    ('falcon', 'Model 9'): None,
    ('kalmar', 'Model 50'): None,
    ('volvo', 'Cab Over Engine HT'): None,
    ('byd', 'Electric Truck Chassis'): None,
    ('frontline', 'Defense - Light'): None,
    ('frontline', 'Defense - Medium'): None,
}
for brand, data in m['brands'].items():
    for model, rec in data.get('models', {}).items():
        b = ''.join(c for c in brand.casefold() if c.isalnum())
        md = ''.join(c for c in model.casefold() if c.isalnum())
        for (tb, tm), _ in targets.items():
            if b == tb and md == tm:
                targets[(tb, tm)] = (brand, model, rec)
for (tb, tm), v in targets.items():
    print('\n###', tb, tm)
    if v is None:
        print('   NOT FOUND')
        continue
    _, _, rec = v
    print('   filePage:', rec.get('filePage'))
    print('   desc:', str(rec.get('description', ''))[:240])
    print('   path:', rec.get('path'))