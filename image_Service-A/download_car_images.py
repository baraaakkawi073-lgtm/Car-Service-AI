#!/usr/bin/env python3
"""
Car-Service-AI image downloader
Downloads one representative vehicle image for every Brand/Model entry
from the supplied "Pasted text.txt" catalog.

Source: Wikimedia Commons via the public MediaWiki API.
The script is resumable: existing images are skipped.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image
from io import BytesIO

API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = (
    "Car-Service-AI-image-downloader/1.0 "
    "(local project; respectful automated requests)"
)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

def parse_catalog(path: Path):
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    # Entries are stored as: **MANUFACTURER:** Model; Model; Model.
    pattern = re.compile(r"\*\*(.+?):\*\*\s*(.*?)(?=\r?\n\r?\n|\Z)", re.S)
    entries = []
    for match in pattern.finditer(text):
        brand = re.sub(r"\s+", " ", match.group(1)).strip()
        models_text = re.sub(r"\s+", " ", match.group(2)).strip()
        models_text = models_text.rstrip(".").strip()
        if not models_text:
            continue

        for raw_model in models_text.split(";"):
            model = raw_model.strip().strip(".")
            if not model:
                continue
            entries.append((brand, model))

    # De-duplicate while preserving order.
    seen = set()
    unique = []
    for brand, model in entries:
        key = (brand.casefold(), model.casefold())
        if key not in seen:
            seen.add(key)
            unique.append((brand, model))
    return unique

def slug(value: str) -> str:
    value = value.lower().strip()
    value = value.replace("&", "and")
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    value = re.sub(r"[\s_-]+", "-", value)
    return value.strip("-") or "unknown"

def safe_name(brand: str, model: str) -> str:
    return f"{slug(brand)}__{slug(model)}"

def search_commons(session: requests.Session, brand: str, model: str):
    # Several queries improve recall while keeping the result reviewable.
    queries = [
        f"{brand} {model} automobile",
        f"{brand} {model} car",
        f"{brand} {model} vehicle",
    ]

    for q in queries:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": q,
            "gsrnamespace": 6,  # File namespace
            "gsrlimit": 10,
            "prop": "imageinfo",
            "iiprop": "url|mime|size|extmetadata",
            "iiurlwidth": 1400,
            "format": "json",
            "formatversion": "2",
            "origin": "*",
        }
        r = session.get(API_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        pages = data.get("query", {}).get("pages", [])

        # Prefer files whose title contains both brand and model terms.
        terms = [t.casefold() for t in re.findall(r"[A-Za-z0-9]+", f"{brand} {model}")]
        ranked = []
        for page in pages:
            info = (page.get("imageinfo") or [{}])[0]
            mime = (info.get("mime") or "").lower()
            url = info.get("thumburl") or info.get("url")
            title = page.get("title", "")
            title_cf = title.casefold()

            if not url or not mime.startswith("image/"):
                continue

            score = 0
            if brand.casefold() in title_cf:
                score += 5
            if model.casefold() in title_cf:
                score += 8
            score += sum(1 for t in terms if t in title_cf)
            # Prefer common photographic formats.
            if mime in {"image/jpeg", "image/webp", "image/png"}:
                score += 1

            ranked.append((score, page))

        ranked.sort(key=lambda x: x[0], reverse=True)
        if ranked:
            return ranked[0][1]

    return None

def get_image_info(page):
    info = (page.get("imageinfo") or [{}])[0]
    return {
        "page_title": page.get("title", ""),
        "url": info.get("url", ""),
        "thumburl": info.get("thumburl", ""),
        "mime": info.get("mime", ""),
        "descriptionurl": info.get("descriptionurl", ""),
        "extmetadata": info.get("extmetadata") or {},
    }

def meta_value(meta, key):
    value = meta.get(key, {})
    if isinstance(value, dict):
        return value.get("value", "")
    return str(value or "")

def download_and_convert(session, url: str, target: Path):
    r = session.get(url, timeout=60)
    r.raise_for_status()

    content_type = r.headers.get("Content-Type", "")
    if not content_type.startswith("image/"):
        raise ValueError(f"Not an image response: {content_type}")

    image = Image.open(BytesIO(r.content))
    image = image.convert("RGB")

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp.webp")
    image.save(tmp, "WEBP", quality=88, method=6)
    tmp.replace(target)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog",
        default="Pasted text.txt",
        help="Catalog text file containing the 3,591 entries.",
    )
    parser.add_argument(
        "--output",
        default=r"image\vehicles",
        help=r"Output directory, relative to the project root.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.35,
        help="Delay between Wikimedia requests in seconds.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Download only the first N entries (0 = all).",
    )
    args = parser.parse_args()

    catalog = Path(args.catalog)
    if not catalog.exists():
        print(f"ERROR: Catalog not found: {catalog}")
        print("Put 'Pasted text.txt' beside this script or use --catalog PATH")
        sys.exit(1)

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    entries = parse_catalog(catalog)
    if args.limit:
        entries = entries[:args.limit]

    print(f"Catalog entries found: {len(entries)}")
    print(f"Output directory: {output.resolve()}")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    csv_path = output / "image_sources.csv"
    existing = {}
    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                existing[row.get("key", "")] = row

    fieldnames = [
        "key", "brand", "model", "status", "local_file",
        "commons_title", "source_url", "description_url",
        "license", "artist", "error",
    ]

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        ok = 0
        missing = 0
        failed = 0

        for index, (brand, model) in enumerate(entries, 1):
            key = f"{brand}|{model}"
            filename = safe_name(brand, model) + ".webp"
            target = output / slug(brand) / filename

            if target.exists() and target.stat().st_size > 1000:
                row = existing.get(key, {})
                row.update({
                    "key": key, "brand": brand, "model": model,
                    "status": "already_exists",
                    "local_file": str(target).replace("\\", "/"),
                    "error": "",
                })
                writer.writerow({k: row.get(k, "") for k in fieldnames})
                ok += 1
                print(f"[{index}/{len(entries)}] EXISTS  {brand} / {model}")
                continue

            try:
                page = search_commons(session, brand, model)
                time.sleep(args.delay)

                if not page:
                    missing += 1
                    writer.writerow({
                        "key": key, "brand": brand, "model": model,
                        "status": "missing", "local_file": "",
                        "commons_title": "", "source_url": "",
                        "description_url": "", "license": "",
                        "artist": "", "error": "No suitable Commons result",
                    })
                    print(f"[{index}/{len(entries)}] MISSING {brand} / {model}")
                    continue

                info = get_image_info(page)
                download_url = info["thumburl"] or info["url"]
                download_and_convert(session, download_url, target)

                license_text = meta_value(info["extmetadata"], "LicenseShortName")
                artist = meta_value(info["extmetadata"], "Artist")

                writer.writerow({
                    "key": key,
                    "brand": brand,
                    "model": model,
                    "status": "downloaded",
                    "local_file": str(target).replace("\\", "/"),
                    "commons_title": info["page_title"],
                    "source_url": info["url"],
                    "description_url": info["descriptionurl"],
                    "license": license_text,
                    "artist": artist,
                    "error": "",
                })
                ok += 1
                print(f"[{index}/{len(entries)}] OK      {brand} / {model}")

            except Exception as exc:
                failed += 1
                writer.writerow({
                    "key": key, "brand": brand, "model": model,
                    "status": "failed", "local_file": "",
                    "commons_title": "", "source_url": "",
                    "description_url": "", "license": "",
                    "artist": "", "error": str(exc)[:500],
                })
                print(f"[{index}/{len(entries)}] ERROR   {brand} / {model}: {exc}")

            f.flush()

    print("\nDONE")
    print(f"Downloaded/existing: {ok}")
    print(f"Missing:             {missing}")
    print(f"Failed:              {failed}")
    print(f"CSV report:          {csv_path.resolve()}")

if __name__ == "__main__":
    main()
