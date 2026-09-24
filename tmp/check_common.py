import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')
assets = json.loads(open('src/ai_report/static/vehicle_assets.js', encoding='utf-8').read().split('=', 1)[1].rstrip(';\n'))
imgs = assets['images']
def key(v): return re.sub(r'[^a-z0-9]', '', (v or '').lower())
# check common model names a user would pick via NHTSA live list
checks = ['Ford F-150','Ford F250','Ford Mustang','Ford Explorer','Ford Transit','Chevrolet Silverado','Chevrolet Camaro',
          'Toyota Camry','Toyota Corolla','Toyota Tundra','Toyota Tacoma','Honda Civic','Honda Accord','Nissan Altima',
          'GMC Sierra','GMC Terrain','Dodge Ram','Dodge Challenger','Jeep Grand Cherokee','BMW 320','Mercedes C300',
          'Kia Rio','Hyundai Elantra','Volkswagen Golf','Audi Q5','Range Rover','Land Cruiser','Tesla Model 3']
for c in checks:
    m = re.match(r'([A-Za-z ]+?)\s+([\S].*)$', c)
    b, mod = m.group(1).strip(), m.group(2).strip()
    got = imgs.get(key(b), {}).get(key(mod))
    print(('OK  ' if got else 'ICON'), c, '->', (got['path'] if got else '(no local photo -> icon)'))