import json, os, sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = r"C:\workbench\fast_api\Car-Service-AI"
m = json.load(open(ROOT + r"\vehicle-images-manifest.json", encoding="utf-8"))

verified = 0
missing_on_disk = []
model_years = 0
for brand, bd in m["brands"].items():
    for name, ent in (bd.get("models") or {}).items():
        if ent.get("status") == "verified":
            verified += 1
            if ent.get("modelYears"):
                model_years += 1
            rel = ent.get("image", "").lstrip("/")
            if not os.path.exists(os.path.join(ROOT, rel.replace("/", "\\"))):
                missing_on_disk.append(rel)

print("verified records:", verified)
print("with modelYears:", model_years)
print("missing on disk:", len(missing_on_disk))
for x in missing_on_disk[:10]:
    print("  ", x)
print("brands:", len(m["brands"]))

# Check the 'non-verified' leftovers that still say 'unresolved'
import collections
c = collections.Counter()
for brand, bd in m["brands"].items():
    for name, ent in (bd.get("models") or {}).items():
        c[ent.get("status")] += 1
print("status counts:", dict(c))