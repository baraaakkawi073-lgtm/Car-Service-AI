"""Fetch Wikimedia Commons photos for the 3,591 missing catalog entries.

Resumable: entries already `downloaded` in the manifest (with a present local
file) are skipped. Results are written back to vehicle-images-manifest.json as
they complete, so an interrupted run can be restarted.

Policy (same spirit as the asset audit):
  * Photo must be a real raster photograph (bitmap filetype, jpg/jpeg/png/webp).
  * Filename must contain the brand and model tokens (intitle search + ranking)
    so a wrongly-matched car is never used.
  * License must be reusable: CC BY / CC0 / Public domain / PDM.
  * Images are resized to at most 640x440 and stored as WebP.
"""
import hashlib
import html
import io
import json
import re
import sys
import time
import threading
import unicodedata
from pathlib import Path
from urllib.parse import quote

import httpx
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
HEADERS = {'User-Agent': 'CarServiceAI/1.1 (https://github.com/anomalyco/opencode; vehicle photo lookup for a car-maintenance assistant) python-httpx/0.27'}
CLIENT = httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True)
COMMONS = 'https://commons.wikimedia.org/w/api.php'
GATE = threading.Lock()
NEXT_REQUEST = 0.0


def get(**params):
    global NEXT_REQUEST
    for attempt in range(5):
        with GATE:
            delay = NEXT_REQUEST - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            NEXT_REQUEST = time.monotonic() + 0.25
        r = CLIENT.get(COMMONS, params=params)
        if r.status_code != 429:
            return r
        pause = max(1, int(r.headers.get('retry-after', '60')))
        with GATE:
            NEXT_REQUEST = max(NEXT_REQUEST, time.monotonic() + pause)
    return r


def key(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s).casefold() if c.isalnum())


def slug(s):
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    s = re.sub(r'[#/\\&+]', '-', s).replace('"', '').replace("'", "")
    return s.lower().replace(' ', '-')

def clean(v):
    return html.unescape(re.sub('<[^>]+>', '', str(v or ''))).strip()


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def write(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def commons_search(intitle_terms, plain=None, limit=10):
    """Search Commons files. Returns list of {title, mime, width, height, thumburl, url}."""
    if intitle_terms:
        q = ' '.join(f'intitle:"{t}"' for t in intitle_terms) + ' filetype:bitmap'
    else:
        q = (plain or '') + ' filetype:bitmap'
    r = get(action='query', format='json', generator='search', gsrsearch=q,
            gsrnamespace='6', gsrlimit=str(limit), prop='imageinfo',
            iiprop='url|mime|size', iiurlwidth='960')
    if r.status_code != 200:
        return []
    out = []
    for p in (r.json().get('query', {}).get('pages', {}) or {}).values():
        ii = (p.get('imageinfo') or [{}])[0]
        out.append({'title': p.get('title', ''), 'mime': ii.get('mime', ''),
                    'width': ii.get('width', 0), 'height': ii.get('height', 0),
                    'thumburl': ii.get('thumburl', ''), 'url': ii.get('url', ''),
                    'filepage': ii.get('descriptionurl', '')})
    out.sort(key=lambda x: x.get('index', 99) if isinstance(x.get('index'), int) else 99)
    return out


def model_search_terms(brand, model):
    """Alternative token sets to try for a (brand, model)."""
    model_base = re.sub(r'\s*\([^)]*\)', ' ', model)
    model_base = model_base.replace('/', ' ').replace('&', ' ').replace('+', ' ')
    tokens = model_base.split()
    terms = [t for t in tokens if t.strip()]
    return terms


def rank_candidates(brand, model, candidates):
    """Return best candidate by filename token overlap, else None."""
    brand_tok = set(re.findall(r'[a-z0-9]+', brand.casefold()))
    model_tok = set(re.findall(r'[a-z0-9]+', re.sub(r'\s*\([^)]*\)', ' ', model).casefold()))
    best = None
    best_score = -1
    for c in candidates:
        title = c['title'].removeprefix('File:')
        mime = (c['mime'] or '').lower()
        if mime not in ('image/jpeg', 'image/png', 'image/webp'):
            continue
        if c['width'] < 500:
            continue
        title_tok = set(re.findall(r'[a-z0-9]+', title.casefold()))
        brand_hit = brand_tok & title_tok
        model_hit = model_tok & title_tok
        # Every brand token must appear (avoids picking some other brand's car).
        brand_ratio = len(brand_hit) / max(1, len(brand_tok))
        model_ratio = len(model_hit) / max(1, len(model_tok))
        if brand_ratio < 1.0:
            continue
        score = model_ratio * 10 + (1.0 if mime == 'image/jpeg' else 0.4)
        if model_ratio > 0:
            score += min(2.0, c['width'] / 2000)
        if score > best_score:
            best_score = score
            best = c
    return best


def ext_metadata(title):
    r = get(action='query', format='json', prop='imageinfo', iiprop='extmetadata',
            titles=title)
    if r.status_code != 200:
        return {}
    pages = (r.json().get('query', {}).get('pages', {}) or {}).values()
    for p in pages:
        ii = (p.get('imageinfo') or [{}])[0]
        return ii.get('extmetadata', {})
    return {}


def acceptable_license(name):
    name = (name or '').strip()
    return name.startswith('CC BY') or name.startswith('CC0') or \
        'Public domain' in name or name in ('PDM', 'CC0')


def fetch_one(brand, model):
    """Return manifest record dict (status downloaded/missing) for one entry."""
    result = {'verifiedModel': True, 'scope': 'model', 'year': None, 'market': 'unknown',
              'sourceType': 'wikimedia_commons', 'imageSource': 'Wikimedia Commons'}
    terms = model_search_terms(brand, model)
    if not terms:
        return dict(result, status='missing', reason='No usable model tokens')
    candidates = commons_search([brand] + [terms[0]])
    if not candidates:
        candidates = commons_search([brand] + terms[:2])
    if not candidates and len(terms) > 1:
        candidates = commons_search(None, plain=f'{brand} {model}')
    best = rank_candidates(brand, model, candidates)
    if not best:
        return dict(result, status='missing', reason='No matching Commons photograph')
    meta = ext_metadata(best['title'])
    fields = {k: clean(v.get('value', '')) for k, v in meta.items()}
    license_name = fields.get('LicenseShortName', '')
    if not acceptable_license(license_name):
        return dict(result, status='missing', reason='Photo license not reusable',
                    license=license_name)
    if not best['thumburl']:
        return dict(result, status='missing', reason='No thumbnail available')
    try:
        src = CLIENT.get(best['thumburl'])
        src.raise_for_status()
        if len(src.content) > 8_000_000:
            return dict(result, status='missing', reason='Oversized source')
        img = Image.open(io.BytesIO(src.content))
        if img.width < 180 or img.height < 90:
            return dict(result, status='missing', reason='Photo too small')
        img.thumbnail((640, 440))
        path = Path('image/vehicles') / slug(brand) / (slug(model) + '.webp')
        (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
        img.convert('RGB').save(ROOT / path, 'WEBP', quality=80, method=6)
        result.update(status='downloaded', path='/' + path.as_posix(),
                      sourceUrl=best['thumburl'], sourcePage=best['filepage'],
                      attribution=fields.get('Artist', ''),
                      license=license_name,
                      licenseUrl=fields.get('LicenseUrl', ''),
                      description=fields.get('ImageDescription', ''),
                      filePage=best['filepage'],
                      modification='Resized to at most 640×440 and converted to WebP',
                      sha256=hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
        return result
    except Exception as exc:
        return dict(result, status='missing', reason=type(exc).__name__ + ' downloading photo')


def main():
    entries = read('tmp/missing-entries-parsed.json')
    manifest = read('vehicle-images-manifest.json')
    brands = manifest.setdefault('brands', {})
    stats = {'done': 0, 'downloaded': 0, 'missing': 0, 'skipped_existing': 0}
    for brand, models in entries.items():
        record = brands.setdefault(brand, {'models': {}})
        record['models'] = record.setdefault('models', {})
        for model in models:
            existing = record['models'].get(model, {})
            existing_path = (existing.get('path') or '')
            if existing.get('status') == 'downloaded' and (ROOT / existing_path.lstrip('/')).is_file():
                stats['skipped_existing'] += 1
                continue
            try:
                photo = fetch_one(brand, model)
            except Exception as exc:
                photo = dict({'verifiedModel': True, 'scope': 'model', 'year': None,
                              'market': 'unknown'}, status='missing',
                             reason=type(exc).__name__ + ' while searching')
            record['models'][model] = photo
            stats['done'] += 1
            stats['downloaded' if photo['status'] == 'downloaded' else 'missing'] += 1
            if stats['done'] % 10 == 0:
                write('vehicle-images-manifest.json', manifest)
            print(f"[{stats['done']}] {brand} | {model} -> {photo['status']} "
                  f"{'' if photo['status']=='downloaded' else photo.get('reason','')}", flush=True)
    write('vehicle-images-manifest.json', manifest)
    write('tmp/vehicle-missing-fetch-stats.json', stats)
    print('DONE', stats, flush=True)


if __name__ == '__main__':
    main()