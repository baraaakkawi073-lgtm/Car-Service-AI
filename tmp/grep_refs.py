import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
pats = ['one:1', 'koenigsegg/one.webp', 'koenigsegg/one"', 'image/vehicles/koenigsegg/one', '/one"', 'one-1.webp']
hits = {}
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ('.git', '.venv', '__pycache__', 'node_modules', '.pytest_cache')]
    for f in files:
        p = os.path.join(root, f)
        if f.endswith(('.png', '.webp', '.jpg', '.ico', '.woff2', '.woff', '.ttf', '.gif', '.pyc')):
            continue
        try:
            t = open(p, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        for pat in pats:
            c = t.count(pat)
            if c:
                hits.setdefault(p, []).append((pat, c))
for p, lst in sorted(hits.items()):
    print(p, '->', lst)