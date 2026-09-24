import json, re, sys

sys.stdout.reconfigure(encoding="utf-8")

JS = r"C:\workbench\fast_api\Car-Service-AI\src\ai_report\static\diagnose.js"
js = open(JS, encoding="utf-8").read()
start = js.index("const CAR_BRANDS")
end = js.index("/* ---- Vehicle image mapping")
block = js[start:end]

brands = []
for m in re.finditer(r"""\{ name: "([^"]+)", logo: "([^"]+)", models: \[(.*?)\] \}""", block, re.S):
    models = re.findall(r'"([^"]+)"', m.group(3))
    brands.append((m.group(1), models))

mf = json.load(open(r"C:\workbench\fast\Car-Service-AI\vehicle-images-manifest.json", encoding="utf-8"))
ma = json.load(open(r"C:\workbench\fast_api\Car-Service-AI\vehicle-images-manifest.json", encoding="utf-8"))

def norm(s):
    return " ".join((s or "").casefold().split())

wiz_missing_fast = []
wiz_missing_fastapi = []
for b, models in brands:
    fb = {norm(k): v for k, v in (mf["brands"].get(b, {}).get("models") or {}).items()}
    ab = {norm(k): v for k, v in (ma["brands"].get(b, {}).get("models") or {}).items()}
    for my in models:
        e = fb.get(norm(my))
        ea = ab.get(norm(my))
        if not e or e.get("status") != "downloaded":
            wiz_missing_fast.append((b, my, (e or {}).get("status") if e else None))
        if not ea or ea.get("status") != "verified":
            wiz_missing_fastapi.append((b, my, (ea or {}).get("status") if ea else None))

print("wizard count:", len(brands), "| models total:", sum(len(x[1]) for x in brands))
print("wizard models NOT downloaded in fast:", len(wiz_missing_fast))
print("wizard models NOT verified in fast_api:", len(wiz_missing_fastapi))
print("sample missing-fast:", wiz_missing_fast[:8])