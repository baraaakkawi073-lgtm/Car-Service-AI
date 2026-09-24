import json, re, sys, pathlib

sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(r"C:\workbench\fast\Car-Service-AI")
va = json.loads(re.search(r"window\.CSAI_VEHICLE_ASSETS = (\{.*\});\s*$",
                          (ROOT / "src/ai_report/static/vehicle_assets.js").read_text(encoding="utf-8"), re.S).group(1))

missing = []
total = 0
for brand_key, models in va["images"].items():
    for mkey, meta in models.items():
        total += 1
        rel = meta["path"].lstrip("/")
        if not (ROOT / rel).is_file():
            missing.append(meta["path"])
for bkey, logo in va["logos"].items():
    rel = logo.lstrip("/")
    if not (ROOT / rel).is_file():
        missing.append("LOGO:" + logo)

print("total images in asset map:", total)
print("missing files referenced (images+logos):", len(missing))
for x in missing[:15]:
    print("  ", x)