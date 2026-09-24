"""Merge case-duplicate brand records (e.g. BUGATTI -> Bugatti).

The pasted registry used ALL-CAPS brand names, so the fetcher created
'BUGATTI' next to the canonical 'Bugatti'. Re-fetches overwrote some
shared files, leaving the canonical record's sha256 stale. This merges
colliding brand keys: the canonical (logo-bearing / Title-case) brand
survives, models are combined, and for a model whose slug path collides
we keep the record whose sha256 matches the file now on disk (typically
the freshly fetched one, whose attribution also matches the current file).
"""
import json, sys, hashlib
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
def key(s): return ''.join(c for c in s.casefold() if c.isalnum())
def slug(s): return key(s)

mpath = ROOT / 'vehicle-images-manifest.json'
m = json.loads(mpath.read_text(encoding='utf-8'))
brands = m['brands']

def disk_matches(rec):
    if rec.get('status') != 'downloaded':
        return None
    fp = ROOT / (rec.get('path') or '').lstrip('/')
    if not fp.exists():
        return False, None
    return True, hashlib.sha256(fp.read_bytes()).hexdigest()

# group brands by normalized key
groups = {}
for b in brands:
    groups.setdefault(key(b), []).append(b)

merged_count = 0
for canonlike, members in groups.items():
    if len(members) < 2:
        continue
    # canonical is the one with a logo; tie-break by Title-case, then alphabetic
    withlogo = [b for b in members if brands[b].get('logo')]
    canonical = withlogo[0] if withlogo else min(members, key=lambda b: key(b))
    dupes = [b for b in members if b != canonical]
    merged_count += len(dupes)
    for d in dupes:
        for model, rec in (brands[d].get('models') or {}).items():
            target = None
            for other_model, other_rec in (brands[canonical].get('models') or {}).items():
                if slug(model) == slug(other_model):
                    target = other_model
                    break
            if target is None:
                brands[canonical].setdefault('models', {})[model] = rec
                continue
            # same slug model in both brands; keep the record matching current disk
            ok1, sha1 = disk_matches(rec)
            ok2, sha2 = disk_matches(brands[canonical]['models'][target])
            existing = brands[canonical]['models'][target]
            if ok1 and sha1 == rec.get('sha256'):
                # latest fetch matches disk -> prefer it (attribution is current)
                if not (ok2 and sha2 == existing.get('sha256')):
                    brands[canonical]['models'][target] = rec
            elif ok2 and sha2 == existing.get('sha256'):
                pass  # already correct
            else:
                # ambiguous; refresh sha from disk on existing record
                if ok2:
                    brands[canonical]['models'][target]['sha256'] = sha2
        del brands[d]

# also merge within-brand model keys that normalize identically
# (e.g. GranCabrio/Grancabrio, Senna/SENNA, H Series/H-Series)
within = 0
for b, rec in brands.items():
    models = rec.get('models') or {}
    seen = {}
    for mod in models:
        seen.setdefault(key(mod), []).append(mod)
    for kk, members in seen.items():
        if len(members) < 2:
            continue
        within += len(members) - 1
        canonical_model = min(members, key=lambda s: (not s[:1].isupper(), -len(s), s))
        dupes_m = [s for s in members if s != canonical_model]
        for d in dupes_m:
            rec_model = models.pop(d)
            cur = models[canonical_model]
            m1 = disk_matches(rec_model)
            m2 = disk_matches(cur)
            ok1, sha1 = m1 if m1 else (False, None)
            ok2, sha2 = m2 if m2 else (False, None)
            if ok1 and sha1 == rec_model.get('sha256'):
                if not (ok2 and sha2 == cur.get('sha256')):
                    models[canonical_model] = rec_model
            elif ok2 and sha2 == cur.get('sha256'):
                pass
            elif ok2:
                models[canonical_model]['sha256'] = sha2

mpath.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
print('merged duplicate brand records:', merged_count)
print('merged within-brand model duplicates:', within)
print('brands now:', len(brands))