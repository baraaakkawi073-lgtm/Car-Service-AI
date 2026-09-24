import json, re, sys

sys.stdout.reconfigure(encoding="utf-8")

js = open(r"C:\workbench\fast\Car-Service-AI\src\ai_report\static\vehicle_assets.js", encoding="utf-8").read()

# parse window.CSAI_VEHICLE_ASSETS = {...};
m = re.search(r"window\.CSAI_VEHICLE_ASSETS\s*=\s*({.*?});\s*$", js, re.S)
obj = json.loads(m.group(1))
images = obj.get("images", {})
logos = obj.get("logos", {})
print("brand keys in images:", len(images))
print("logo keys:", len(logos))
print("ford present:", "ford" in images, "| f-150:", "f-150" in images.get("ford", {}))
ford = images.get("ford", {})
print("sample ford models:", list(ford.keys())[:10])
probes = ["camry", "civic", "corolla", "golf", "land-cruiser", "911", "xc60", "mokka", "hilux", "silverado"]
for brand, models in images.items():
    for p in probes:
        if p in models:
            print(f"{brand}/{p} ->", models[p].get("path", "")[:70])
# count total model entries
c = sum(len(v) for v in images.values())
print("total model entries:", c)