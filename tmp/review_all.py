import json
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
cur = json.load(open('vehicle-images-manifest.json', encoding='utf-8'))
head = json.loads(subprocess.check_output(['git', 'show', 'HEAD:vehicle-images-manifest.json'], encoding='utf-8'))

# files modified on disk
mod = subprocess.check_output(['git', 'status', '--short'], encoding='utf-8').splitlines()
modpath = set()
for line in mod:
    fp = line[3:].strip()
    if fp.startswith('image/vehicles/') and fp.endswith('.webp'):
        modpath.add(fp.replace('/', '\\'))

# build manifest path -> record
cur_by_path = {}
head_by_path = {}
for data, container in ((cur, cur_by_path), (head, head_by_path)):
    for brand, bdata in data['brands'].items():
        for model, rec in bdata.get('models', {}).items():
            p = (rec.get('path') or '').lstrip('/').replace('/', '\\')
            container[p] = (brand, model, rec)

for p in sorted(modpath):
    c = cur_by_path.get(p)
    h = head_by_path.get(p)
    print('\n###', p.replace('\\', '/'))
    if h:
        print('  HEAD:', h[1], '|', h[2].get('filePage'))
        print('     ', str(h[2].get('description', ''))[:140])
    if c:
        print('  CUR :', c[1], '|', c[2].get('filePage'))
        print('     ', str(c[2].get('description', ''))[:140])