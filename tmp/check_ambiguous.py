import collections, json, sys

sys.stdout.reconfigure(encoding="utf-8")

m = json.load(open(r"C:\workbench\fast\Car-Service-AI\vehicle-images-manifest.json", encoding="utf-8"))
c = collections.Counter()
amb = []
for brand, bd in m["brands"].items():
    for name, ent in (bd.get("models") or {}).items():
        c[ent.get("status")] += 1
        if ent.get("status") == "ambiguous-duplicate":
            amb.append((brand, name, ent.get("path")))
print("status counts:", dict(c))
print("ambiguous-duplicate count:", len(amb))
for x in amb[:15]:
    print("  ", x)