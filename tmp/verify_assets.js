import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
s = Path('src/ai_report/static/vehicle_assets.js').read_text(encoding='utf-8')
data = json.loads(s[s.index('{'):])
logos = data['logos']; images = data['images']
print('logos:', len(logos), '| brands with images:', len(images), '| models:', sum(len(v) for v in images.values()))
checks = [('peterbilt', '579'), ('am-general', 'mv1'), ('ferrari', 'lafarari'),
          ('volvo', 'vnl'), ('tesla', 'cybertruck'), ('international', '9900i')]
for b, m in checks:
    rec = images.get(b, {}).get(m)
    print(f"{b}/{m}:", rec.get('path') if rec else 'MISSING')