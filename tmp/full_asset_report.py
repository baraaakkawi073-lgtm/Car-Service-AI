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

# manifest lookup map by key
man_map = {}
for b, data in manifest['brands'].items():
    for m, r in data['models'].items():
        man_map[(key(b), key(m))] = (b, m, r)

problems = defaultdict(list)
dup_groups = defaultdict(list)
missing_records = []
size_bad = []
manifest_sha_bad = []
non_ascii_paths = []
n = 0
for brand, models in assets['images'].items():
    for model, photo in models.items():
        n += 1
        rel = photo['path'].lstrip('/')
        if not rel.isascii():
            non_ascii_paths.append((brand, model, rel))
        path = ROOT / rel
        if not path.is_file():
            problems['missing_file'].append((brand, model, rel))
            continue
        size = path.stat().st_size
        if not (0 < size < 250_000):
            size_bad.append((brand, model, rel, size))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        dup_groups[digest].append(f'{brand}/{model}')
        rec = man_map.get((key(brand), key(model)))
        if rec is None:
            missing_records.append((brand, model, rel))
            continue
        r = rec[2]
        if r.get('sha256') != digest:
            manifest_sha_bad.append((brand, model, rel, r.get('sha256'), digest))

print('TOTAL CONNECTED MODELS:', n)
print()
print('== MODELS WITHOUT A MATCHING MANIFEST RECORD (%d) ==' % len(missing_records))
for x in missing_records:
    print('  ', x)
print()
print('== NON-ASCII PATHS (%d) ==' % len(non_ascii_paths))
for x in non_ascii_paths:
    print('  ', x)
print()
print('== SIZE OUT OF RANGE (%d) ==' % len(size_bad))
for x in size_bad:
    print('  ', x)
print()
print('== MANIFEST SHA256 MISMATCH (%d) ==' % len(manifest_sha_bad))
for x in manifest_sha_bad:
    print('  ', x)
print()
real_dups = {d: v for d, v in dup_groups.items() if len(v) > 1}
print('== CONNECTED DUPLICATE DIGEST GROUPS (%d) ==' % len(real_dups))
for d, v in sorted(real_dups.items()):
    print(d[:12], '(%d):' % len(v), ', '.join(v))

from collections import Counter
import os
all_files = set()
for root, dirs, files in os.walk(ROOT / 'image/vehicles'):
    for f in files:
        all_files.add(os.path.relpath(os.path.join(root, f), ROOT).replace('\\', '/'))
connected_paths = set()
for models in assets['images'].values():
    for photo in models.values():
        connected_paths.add(photo['path'].lstrip('/'))
unused = sorted(all_files - connected_paths)
print()
print('== UNUSED vehicle image files on disk (%d) ==' % len(unused))
for u in unused:
    print('   ', u)