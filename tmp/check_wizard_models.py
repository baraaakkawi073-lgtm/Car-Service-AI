import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')
# extract CAR_BRANDS from diagnose.js
s = open('src/ai_report/static/diagnose.js', encoding='utf-8').read()
mm = re.search(r'const CAR_BRANDS = \[(.*?)\];', s, re.S)
brands = re.findall(r'\{\s*name:\s*"([^"]+)",\s*logo:\s*[^,]+,\s*models:\s*\[(.*?)\]\s*\}', mm.group(1))
car_brands = {}
for name, models in brands:
    car_brands[name] = [m.strip().strip('"\'') for m in models.split(',') if m.strip()]

# assets image keys
assets = json.loads(open('src/ai_report/static/vehicle_assets.js', encoding='utf-8').read().split('=', 1)[1].rstrip(';\n'))
imgs = assets['images']

def key(v): return re.sub(r'[^a-z0-9]', '', (v or '').lower())
missing_in_wizard = []
have = 0
for b, ms in car_brands.items():
    for m in ms:
        if imgs.get(key(b), {}).get(key(m)):
            have += 1
        else:
            missing_in_wizard.append((b, m))
print('wizard CAR_BRANDS brands:', len(car_brands))
print('models shown in wizard picker:', sum(len(v) for v in car_brands.values()))
print('  with local photo:', have)
print('  WITHOUT local photo:', len(missing_in_wizard))
print('--- wizard models without local photo ---')
for b, m in missing_in_wizard:
    print(f'  {b} | {m}')