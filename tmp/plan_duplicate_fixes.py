import hashlib
import json
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def key(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value).casefold() if c.isalnum())


source = (ROOT / 'src/ai_report/static/vehicle_assets.js').read_text(encoding='utf-8')
assets = json.loads(source.split(' = ', 1)[1].rstrip(';\n'))
manifest = json.loads((ROOT / 'vehicle-images-manifest.json').read_text(encoding='utf-8'))

man_map = {}
for b, data in manifest['brands'].items():
    for m, r in data['models'].items():
        man_map[(key(b), key(m))] = (b, m, r)

dup_groups = defaultdict(list)
for brand, models in assets['images'].items():
    for model, photo in models.items():
        rel = photo['path'].lstrip('/')
        path = ROOT / rel
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        dup_groups[digest].append((brand, model, rel))

real = {d: v for d, v in dup_groups.items() if len(v) > 1}

need_reload = 0      # members whose manifest sourcePage differs from first member -> own source exists
need_search = 0      # members whose sourcePage is same (or missing) -> must find a new photo
plan = {}
for d, members in real.items():
    infos = []
    for brand, model, rel in members:
        b, m, r = man_map[(key(brand), key(model))]
        infos.append({
            'brand': brand, 'model': model, 'rel': rel,
            'display': m,
            'sourcePage': r.get('sourcePage'),
            'sha256': r.get('sha256'),
            'verified': r.get('verifiedModel'),
        })
    keeper = infos[0]
    for info in infos[1:]:
        if info['sourcePage'] and info['sourcePage'] != keeper['sourcePage']:
            info['fix'] = 'REDOWNLOAD_OWN_SOURCE'
            need_reload += 1
        else:
            info['fix'] = 'SEARCH_NEW_IMAGE'
            need_search += 1
    infos[0]['fix'] = 'KEEPER'
    plan[d] = infos

print('Duplicate groups: %d, affected member counts: redownload=%d search=%d' % (
    len(real), need_reload, need_search))
print()
for d, infos in plan.items():
    print('GROUP %s-%s (%d):' % (d[:10], d[10:12], len(infos)))
    for i in infos:
        print('   [%s] %s / %s -> %s   page=%s' % (
            i['fix'], i['brand'], i['model'], i['rel'], i['sourcePage']))

# koenigsegg one:1 special
for brand, models in assets['images'].items():
    for model, photo in models.items():
        if 'one' in model and 'koenigsegg' in brand:
            print()
            print('KOENIGSEGG ONE:1 PATH:', photo['path'])
            print('   file exists:', (ROOT / photo['path'].lstrip('/')).is_file(),
                  'size:', (ROOT / photo['path'].lstrip('/')).stat().st_size if (ROOT / photo['path'].lstrip('/')).exists() else 'n/a')