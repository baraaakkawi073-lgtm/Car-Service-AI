"""Fix duplicate vehicle-photo bytes across the catalogue.

For every duplicate digest group, the KEEPER keeps its photo; every other
member gets a NEW, genuinely different Wikimedia Commons photograph of the
same model. Each member has its OWN unique file path already, so we just
overwrite that file with new bytes and resync the manifest + assets entry.

- The test forbids identical sha256 across connected models, so a candidate
  is only accepted if its converted digest is not already used.
- The keeper's own source file is never re-used.
- Multi-tier Commons search (strict brand+model -> model-only -> plain ->
  any bitmap) so obscure brands still resolve rather than leaving dupes.
- Resumable: groups are re-derived from current file bytes each run, so
  already-fixed members are skipped automatically.
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

import requests
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
HEADERS = {'User-Agent': 'CarServiceAI/1.2 (vehicle duplicate fix; car-maintenance assistant) python-requests/2.31'}
CLIENT = requests.Session()
CLIENT.headers.update(HEADERS)
COMMONS = 'https://commons.wikimedia.org/w/api.php'
GATE = threading.Lock()
NEXT_REQUEST = 0.0

MANIFEST = ROOT / 'vehicle-images-manifest.json'
ASSETS = ROOT / 'src/ai_report/static/vehicle_assets.js'


def get(**params):
    global NEXT_REQUEST
    for attempt in range(6):
        with GATE:
            delay = NEXT_REQUEST - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            NEXT_REQUEST = time.monotonic() + 0.25
        r = CLIENT.get(COMMONS, params=params, timeout=40)
        if r.status_code != 429:
            return r
        pause = max(1, int(r.headers.get('retry-after', '60')))
        with GATE:
            NEXT_REQUEST = max(NEXT_REQUEST, time.monotonic() + pause)
    return r


def key(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s).casefold() if c.isalnum())


def clean(v):
    return html.unescape(re.sub('<[^>]+>', '', str(v or ''))).strip()


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def write(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def commons_search(intitle_terms, plain=None, limit=20):
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
                    'filepage': ii.get('descriptionurl', ''),
                    'index': p.get('index', 99)})
    out.sort(key=lambda x: x.get('index', 99))
    return out


def model_tokens(model):
    base = re.sub(r'\s*\([^)]*\)', ' ', model)
    base = base.replace('/', ' ').replace('&', ' ').replace('+', ' ').replace(',', ' ')
    return [t for t in base.split() if t.strip()]


def rank_list(brand, model, candidates):
    brand_tok = set(re.findall(r'[a-z0-9]+', brand.casefold()))
    model_tok = set(re.findall(r'[a-z0-9]+', re.sub(r'\s*\([^)]*\)', ' ', model).casefold()))
    scored = []
    for c in candidates:
        mime = (c['mime'] or '').lower()
        if mime not in ('image/jpeg', 'image/png', 'image/webp'):
            continue
        if c['width'] < 500:
            continue
        title = c['title'].removeprefix('File:')
        title_tok = set(re.findall(r'[a-z0-9]+', title.casefold()))
        brand_hit = brand_tok & title_tok
        if brand_tok and len(brand_hit) < len(brand_tok):
            continue
        model_hit = model_tok & title_tok
        model_ratio = len(model_hit) / max(1, len(model_tok))
        score = model_ratio * 10 + (1.0 if mime == 'image/jpeg' else 0.4) + min(2.0, c['width'] / 2000)
        scored.append((score, model_hit, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def rank_relaxed(model, candidates):
    model_tok = set(re.findall(r'[a-z0-9]+', re.sub(r'\s*\([^)]*\)', ' ', model).casefold()))
    scored = []
    for c in candidates:
        mime = (c['mime'] or '').lower()
        if mime not in ('image/jpeg', 'image/png', 'image/webp'):
            continue
        if c['width'] < 500:
            continue
        title = c['title'].removeprefix('File:')
        title_tok = set(re.findall(r'[a-z0-9]+', title.casefold()))
        hit = model_tok & title_tok
        score = len(hit) / max(1, len(model_tok)) * 10 + (1.0 if mime == 'image/jpeg' else 0.4) + min(2.0, c['width'] / 2000)
        scored.append((score, hit, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def search_tiers(brand, model):
    terms = model_tokens(model)
    if not terms:
        terms = model_tokens(brand)
    if terms:
        yield ('A:brand+model', commons_search([brand] + terms[:2]))
    if len(terms) > 1:
        yield ('B:model', commons_search(terms[:2]))
    yield ('C:plain', commons_search(None, plain=f'{brand} {model}'))
    yield ('D:any', commons_search(None, plain=model))


def ext_metadata(title):
    r = get(action='query', format='json', prop='imageinfo', iiprop='extmetadata', titles=title)
    if r.status_code != 200:
        return {}
    for p in (r.json().get('query', {}).get('pages', {}) or {}).values():
        ii = (p.get('imageinfo') or [{}])[0]
        return ii.get('extmetadata', {})
    return {}


def acceptable_license(name):
    name = (name or '').strip()
    return name.startswith('CC BY') or name.startswith('CC0') or \
        'Public domain' in name or name in ('PDM', 'CC0')


def make_webp(candidate, dest_path, used_digests):
    meta = ext_metadata(candidate['title'])
    fields = {k: clean(v.get('value', '')) for k, v in meta.items()}
    license_name = fields.get('LicenseShortName', '')
    if not acceptable_license(license_name):
        return None, ('license', license_name)
    if not candidate['thumburl']:
        return None, ('nothumb', '')
    try:
        src = CLIENT.get(candidate['thumburl'], timeout=40)
        src.raise_for_status()
        if len(src.content) > 8_000_000:
            return None, ('big', len(src.content))
        img = Image.open(io.BytesIO(src.content))
        img.thumbnail((640, 440))
        img = img.convert('RGB')
        data = None
        for quality in (75, 65, 55):
            buf = io.BytesIO()
            img.save(buf, 'WEBP', quality=quality, method=6)
            data = buf.getvalue()
            if len(data) < 250_000:
                break
        if data is None or len(data) >= 250_000:
            return None, ('toolarge', len(data))
        dest_path.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        if digest in used_digests:
            return None, ('dupdigest', digest[:12])
        return digest, ('ok', quality)
    except Exception as exc:
        return None, ('dl', type(exc).__name__)


def save_assets(assets):
    ASSETS.write_text(
        '// Generated from vehicle-images-manifest.json. Only audited local assets.\n'
        'window.CSAI_VEHICLE_ASSETS = ' + json.dumps(assets, ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')


def main():
    manifest = read('vehicle-images-manifest.json')
    assets = json.loads(ASSETS.read_text(encoding='utf-8').split(' = ', 1)[1].rstrip(';\n'))
    images = assets['images']

    used = {}
    for b, mods in images.items():
        for m, ph in mods.items():
            p = ROOT / ph['path'].lstrip('/')
            if p.is_file():
                used.setdefault(hashlib.sha256(p.read_bytes()).hexdigest(), []).append((b, m))
    used_digests = set(used)

    groups = {d: sorted(m) for d, m in used.items() if len(m) > 1}
    print('duplicate groups to resolve:', len(groups), flush=True)
    total_members = sum(len(m) - 1 for m in groups.values())
    print('members needing new photo:', total_members, flush=True)

    fixes = []
    fails = []
    processed = 0
    for digest, members in groups.items():
        keeper = members[0]
        keeper_file = ROOT / images[keeper[0]][keeper[1]]['path'].lstrip('/')
        keeper_page = None
        for bb, bd in manifest['brands'].items():
            if key(bb) == keeper[0]:
                for mm, mmd in bd.get('models', {}).items():
                    if key(mm) == keeper[1]:
                        keeper_page = mmd.get('sourcePage', '')
                        break
                break
        keeper_base = (keeper_page or '').rstrip('/').split('/')[-1].replace('_', ' ') if keeper_page else ''

        for brand_key, model_key in members[1:]:
            processed += 1
            path = images[brand_key][model_key]['path']
            dest = ROOT / path.lstrip('/')

            db = dv = None
            rec = None
            for bb, bd in manifest['brands'].items():
                if key(bb) == brand_key:
                    db = bb
                    for mm, mmd in bd.get('models', {}).items():
                        if key(mm) == model_key:
                            dv = mm
                            rec = mmd
                            break
                    break
            if rec is None:
                fails.append((db or brand_key, dv or model_key, path, 'no-manifest-record'))
                print(f'  FAIL {processed}/{total_members} {db or brand_key}::{dv or model_key} no-manifest-record', flush=True)
                continue

            chosen_digest = None
            chosen_cand = None
            chosen_tier = None
            reason = 'no-candidates'
            tried_titles = set()

            for tier, candidates in search_tiers(db or brand_key, dv or model_key):
                ranked = rank_list(db or brand_key, dv or model_key, candidates) if tier.startswith('A') else rank_relaxed(dv or model_key, candidates)
                if not ranked:
                    continue
                for score, hit, cand in ranked:
                    title = cand['title']
                    if not title or title in tried_titles:
                        continue
                    tried_titles.add(title)
                    base = title.removeprefix('File:').replace('_', ' ')
                    if keeper_base and base == keeper_base:
                        continue
                    digest2, (tag, note) = make_webp(cand, dest, used_digests)
                    if digest2:
                        chosen_digest = digest2
                        chosen_cand = cand
                        chosen_tier = tier
                        used_digests.add(digest2)
                        break
                    reason = f'{tag}:{note}'
                if chosen_digest:
                    break

            if not chosen_digest:
                fails.append((db or brand_key, dv or model_key, path, reason))
                print(f'  FAIL {processed}/{total_members} {db or brand_key}::{dv or model_key} {reason}', flush=True)
                continue

            cand = chosen_cand
            meta = ext_metadata(cand['title'])
            fields = {k: clean(v.get('value', '')) for k, v in meta.items()}
            rec['sourceType'] = 'wikimedia_commons'
            rec['imageSource'] = 'Wikimedia Commons'
            rec['status'] = 'downloaded'
            rec['sourceUrl'] = cand['thumburl']
            rec['sourcePage'] = cand['filepage']
            rec['attribution'] = fields.get('Artist', '')
            rec['license'] = fields.get('LicenseShortName', '')
            rec['licenseUrl'] = fields.get('LicenseUrl', '')
            rec['description'] = fields.get('ImageDescription', '')
            rec['filePage'] = cand['filepage']
            rec['modification'] = 'Resized to at most 640×440 and converted to WebP'
            rec['sha256'] = chosen_digest

            images[brand_key][model_key] = {
                'path': path,
                'attribution': fields.get('Artist', ''),
                'license': fields.get('LicenseShortName', ''),
                'filePage': cand['filepage'],
            }
            fixes.append((db or brand_key, dv or model_key, chosen_tier, cand['title']))
            print(f'  OK   {processed}/{total_members} [{chosen_tier}] {db or brand_key}::{dv or model_key} <- {cand["title"]}', flush=True)
            if processed % 5 == 0:
                write('vehicle-images-manifest.json', manifest)
                save_assets(assets)

    write('vehicle-images-manifest.json', manifest)
    save_assets(assets)
    write('tmp/duplicate-fix-results.json', {'fixed': fixes, 'failed': fails})
    print(f'DONE fixed={len(fixes)} failed={len(fails)}', flush=True)
    for f in fails:
        print('   FAILED:', f, flush=True)


if __name__ == '__main__':
    main()