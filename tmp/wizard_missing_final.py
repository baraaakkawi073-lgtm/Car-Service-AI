import json, re, sys, pathlib
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

JS = r"C:\workbench\fast\Car-Service-AI\src\ai_report\static\diagnose.js"
js = open(JS, encoding="utf-8").read()
start = js.index("const CAR_BRANDS")
end = js.index("const VEHICLE_IMAGES") if "const VEHICLE_IMAGES" in js else js.index("function getModelImage")
block = js[start:end]

brands = []
for m in re.finditer(r"""\{ name: "([^"]+)", logo: "([^"]+)", models: \[(.*?)\] \}""", block, re.S):
    models = re.findall(r'"([^"]+)"', m.group(3))
    brands.append((m.group(1), models))

va = json.loads(re.search(r"window\.CSAI_VEHICLE_ASSETS = (\{.*\});\s*$",
                          pathlib.Path(r"C:\workbench\fast\Car-Service-AI\src\ai_report\static\vehicle_assets.js").read_text(encoding="utf-8"),
                          re.S).group(1))
images = va["images"]


def key(s):
    return "".join(c for c in s.casefold() if c.isalnum())


missing = []
for b, models in brands:
    for my in models:
        if not (key(my) in images.get(key(b), {})):
            missing.append((b, my))

print("wizard models WITHOUT local photo:", len(missing))
c = Counter(b for b, _ in missing)
print("by brand:", c.most_common())
print("their list:", missing)