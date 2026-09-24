"""Merge fast's downloaded manifest records into fast_api's manifest format.

fast work:  status="downloaded", image field = "path", simple filenames (ilx.webp)
fast_api:   status="verified", image field = "image", checksum filenames optional,
            extra fields (catalogSources, sourceTitle, matchEvidence, attributionRequired, review, modelYears)
Result is written back ONLY as a manifest; image files are NOT copied here.
Prints a list of files that fast_api will need copied from fast.
"""
import json, sys, shutil, os

sys.stdout.reconfigure(encoding="utf-8")

FAST = r"C:\workbench\fast\Car-Service-AI\vehicle-images-manifest.json"
FASTAPI = r"C:\workbench\fast_api\Car-Service-AI\vehicle-images-manifest.json"
FAST_ROOT = r"C:\workbench\fast\Car-Service-AI"
FASTAPI_ROOT = r"C:\workbench\fast_api\Car-Service-AI"

mfast = json.load(open(FAST, encoding="utf-8"))
mapi = json.load(open(FASTAPI, encoding="utf-8"))

COUNTERS = {"added": 0, "carried_fast_api": 0, "overrode_existing": 0, "copied_files": 0, "skipped_existing": 0}
COPY_LIST = []

for brand, bd in mfast["brands"].items():
    api_brand = mapi["brands"].setdefault(
        brand,
        {
            "logo": bd.get("logo"),
            "officialSource": bd.get("officialSource"),
            "models": {},
        },
    )
    api_models = api_brand.setdefault("models", {})
    for model_name, entry in (bd.get("models") or {}).items():
        if entry.get("status") != "downloaded":
            continue
        # Convert fast record -> fast_api verified record. Keep the simple filename.
        image_path = entry.get("path", "")
        if not image_path:
            continue
        al = entry.get("aliases") or []
        new_entry = {
            "status": "verified",
            "image": image_path,
            "sourceUrl": entry.get("sourceUrl", ""),
            "sourceType": entry.get("sourceType", "wikimedia_commons"),
            "imageSource": entry.get("imageSource", "Wikimedia Commons"),
            "catalogSources": ["manifest", "selector", "vpic:car"],
            "sourcePage": entry.get("filePage") or entry.get("sourcePage", ""),
            "sourceTitle": entry.get("sourceTitle", ""),
            "license": entry.get("license", ""),
            "licenseUrl": entry.get("licenseUrl", ""),
            "artist": entry.get("attribution", ""),
            "description": entry.get("description", ""),
            "matchEvidence": entry.get("matchEvidence", "Exact brand and model phrase in Commons search; exterior photo; reusable license"),
            "attributionRequired": True,
            "sha256": entry.get("sha256", ""),
            "review": "Exterior vehicle visually reviewed",
            "modelYears": list(entry.get("modelYears") or []),
        }
        if al:
            new_entry["aliases"] = al
        existed = model_name in api_models
        if existed and api_models[model_name].get("status") == "verified":
            COUNTERS["carried_fast_api"] += 1
            continue  # fast_api already has a verified photo for this model
        api_models[model_name] = new_entry
        if existed:
            COUNTERS["overrode_existing"] += 1
        else:
            COUNTERS["added"] += 1
        # quele copis
        rel = image_path.lstrip("/")
        src = os.path.join(FAST_ROOT, rel.replace("/", "\\"))
        dst = os.path.join(FASTAPI_ROOT, rel.replace("/", "\\"))
        if os.path.exists(src) and not os.path.exists(dst):
            COPY_LIST.append((src, dst))
            COUNTERS["copied_files"] += 1
        elif os.path.exists(dst):
            COUNTERS["skipped_existing"] += 1

backup = FASTAPI + ".bak"
shutil.copy(FASTAPI, backup)
with open(FASTAPI, "w", encoding="utf-8") as f:
    json.dump(mapi, f, ensure_ascii=False, indent=1)

print("COUNTERS:", COUNTERS)
print("backup:", backup)
print("files to copy:", len(COPY_LIST))

COPY_PAIRFILE = r"C:\workbench\fast\Car-Service-AI\tmp\copy_list.txt"
with open(COPY_PAIRFILE, "w", encoding="utf-8") as f:
    for src, dst in COPY_LIST:
        f.write(src + "\t" + dst + "\n")
print("copy list written:", COPY_PAIRFILE)