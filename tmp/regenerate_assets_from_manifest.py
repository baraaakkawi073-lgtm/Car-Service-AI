"""Regenerate src/ai_report/static/vehicle_assets.js solely from the current
vehicle-images-manifest.json (all downloaded records). Does NOT touch config.py,
the manifest, or any other file. This fixes the earlier assets that were built
from an old 'ambiguous-duplicate' state and dropped ~188 downloaded photos.
"""
import json, shutil, sys, unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\workbench\fast\Car-Service-AI")


def key(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s).casefold() if c.isalnum())


manifest = json.loads((ROOT / "vehicle-images-manifest.json").read_text(encoding="utf-8"))

logos = {}
images = {}
credits = []
downloaded = 0
skip_no_file = []
for brand, bd in manifest["brands"].items():
    brand_key = key(brand)
    logo = bd.get("logo")
    if logo and (ROOT / logo.lstrip("/")).is_file():
        logos[brand_key] = logo
    images[brand_key] = {}
    for model_name, photo in (bd.get("models") or {}).items():
        if photo.get("status") != "downloaded":
            continue
        path = photo.get("path")
        if not path:
            continue
        if not (ROOT / path.lstrip("/")).is_file():
            skip_no_file.append((brand, model_name, path))
            continue
        images[brand_key][key(model_name)] = {
            k: photo[k] for k in ["path", "attribution", "license", "filePage"]
        }
        downloaded += 1
        credits.append({"brand": brand, "model": model_name, **photo})

asset_data = {"logos": logos, "images": images}
out = ROOT / "src/ai_report/static/vehicle_assets.js"
# timestamped safety copy
bak = out.with_suffix(".js.bak")
shutil.copy(out, bak)
out.write_text(
    "// Generated from vehicle-images-manifest.json. Only audited local assets.\n"
    "window.CSAI_VEHICLE_ASSETS = "
    + json.dumps(asset_data, ensure_ascii=False, separators=(",", ":"))
    + ";\n",
    encoding="utf-8",
)

print("logos:", len(logos))
print("images (model entries):", downloaded)
print("skipped (no file on disk):", len(skip_no_file))
for x in skip_no_file[:10]:
    print("  ", x)
print("backup written:", bak)

# sanity: did ford/f-150 make it in this time?
print("ford/f-150 present:", "f150" in images.get(key("Ford"), {}))
print("ford sample:", list(images.get(key("Ford"), {}).keys())[:12])