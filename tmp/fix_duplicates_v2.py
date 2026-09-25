"""Fix remaining duplicate + bad vehicle photos with curated queries.

Only processes a curated redo list keyed by (brand_key, model_key) -> list of
Commons search queries (most specific first). Strict rules:
  * never reuse a sourcePage already used by ANY connected model (kills the
    re-encode-of-keeper problem);
  * accepted digest must be unique across all connected models;
  * prefer jpeg > png, larger width, more model-token title hits;
  * writes file + manifest + assets entry in lockstep.
"""
import hashlib
import html
import io
import json
import re
import sys
import time
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
NEXT_REQUEST = 0.0

MANIFEST = ROOT / 'vehicle-images-manifest.json'
ASSETS = ROOT / 'src/ai_report/static/vehicle_assets.js'


def get(**params):
    global NEXT_REQUEST
    for attempt in range(6):
        delay = NEXT_REQUEST - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        NEXT_REQUEST = time.monotonic() + 0.3
        r = CLIENT.get(COMMONS, params=params, timeout=40)
        if r.status_code != 429:
            return r
        pause = max(1, int(r.headers.get('retry-after', '60')))
        NEXT_REQUEST = time.monotonic() + pause
    return r


def key(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s).casefold() if c.isalnum())


def clean(v):
    return html.unescape(re.sub('<[^>]+>', '', str(v or ''))).strip()


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def write(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def search(q, limit=25):
    r = get(action='query', format='json', generator='search',
            gsrsearch=q, gsrnamespace='6', gsrlimit=str(limit),
            prop='imageinfo', iiprop='url|mime|size', iiurlwidth='960')
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


def score_candidate(cand, brand, model, used_pages):
    mime = (cand['mime'] or '').lower()
    if mime not in ('image/jpeg', 'image/png', 'image/webp'):
        return None, 'mime'
    if cand['width'] < 500:
        return None, 'small'
    base = cand['title'].removeprefix('File:').replace('_', ' ')
    if cand['filepage'] in used_pages:
        return None, 'page-used'
    brand_tok = set(re.findall(r'[a-z0-9]+', brand.casefold()))
    model_tok = set(re.findall(r'[a-z0-9]+', re.sub(r'\s*\([^)]*\)', ' ', model).casefold()))
    title_tok = set(re.findall(r'[a-z0-9]+', base.casefold()))
    bhit = brand_tok & title_tok
    if brand_tok and len(bhit) < len(brand_tok):
        return None, 'brand-mismatch'
    mhit = model_tok & title_tok
    mratio = len(mhit) / max(1, len(model_tok))
    score = mratio * 10 + (1.0 if mime == 'image/jpeg' else 0.4) + min(2.0, cand['width'] / 2000)
    return (score, mratio, cand), None


def make_webp(cand, dest, used_digests):
    meta = ext_metadata(cand['title'])
    fields = {k: clean(v.get('value', '')) for k, v in meta.items()}
    lic = fields.get('LicenseShortName', '')
    if not acceptable_license(lic):
        return None, ('license', lic)
    if not cand['thumburl']:
        return None, ('nothumb', '')
    try:
        src = CLIENT.get(cand['thumburl'], timeout=40)
        src.raise_for_status()
        if len(src.content) > 8_000_000:
            return None, ('big', len(src.content))
        img = Image.open(io.BytesIO(src.content))
        img.thumbnail((640, 440))
        img = img.convert('RGB')
        data = None
        qused = None
        for q in (75, 65, 55):
            buf = io.BytesIO()
            img.save(buf, 'WEBP', quality=q, method=6)
            data = buf.getvalue()
            if len(data) < 250_000:
                qused = q
                break
        if data is None or len(data) >= 250_000:
            return None, ('toolarge', len(data))
        d = hashlib.sha256(data).hexdigest()
        if d in used_digests:
            return None, ('dupdigest', d[:12])
        dest.write_bytes(data)
        return {'sha256': d, 'fields': fields, 'license': lic, 'q': qused}, None
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

    # ----- used digests + used source pages across every connected model -----
    used_digests = set()
    used_pages = set()
    for b, mods in images.items():
        for m, ph in mods.items():
            p = ROOT / ph['path'].lstrip('/')
            if p.is_file():
                used_digests.add(hashlib.sha256(p.read_bytes()).hexdigest())
            for bb, bd in manifest['brands'].items():
                if key(bb) == b:
                    for mm, mmd in bd.get('models', {}).items():
                        if key(mm) == m and mmd.get('sourcePage'):
                            used_pages.add(mmd['sourcePage'])
                    break

    # ----- curated redo list: (brand_key, model_key, [queries]) -----
    redo = [
        # remaining byte-duplicates
        ('bmw', '650ib6', ['"BMW 650i" Gran Coupe', '"BMW 650i" Coupe', 'BMW 650i Individual']),
        ('bmw', '750ib7', ['"BMW 750i"', '"BMW 750i" xDrive', 'BMW 750i F01']),
        ('bmw', '750lialpinab7', ['"BMW 750Li"', '"750Li" BMW', 'BMW Alpina B7']),
        ('chevrolet', 'silveradoltd', ['"Chevrolet Silverado 1500"', '"Chevrolet Silverado" pickup', '"Silverado" 1500']),
        ('isuzu', 'ftrfvrevr', ['Isuzu FTR', 'Isuzu FVR', 'Isuzu forward control truck']),
        ('isuzu', 'nqrnrr', ['Isuzu NQR', 'Isuzu NRR', 'Isuzu truck N-series']),
        ('daewoo', 'leganzav200variantsderivatives', ['"Daewoo Leganza"', 'Daewoo Leganza sedan']),
        ('mahindra', 'mahindratr20', ['"Mahindra TR20"', 'Mahindra mini truck', 'Mahindra truck']),
        ('mahindra', 'mahindratr40', ['"Mahindra TR40"', 'Mahindra truck', 'Mahindra pickup']),
        ('armbrusterstageway', 'cadillacskicruiser', ['Armbruster Cadillac', '"Cadillac" limousine Armbruster', 'Cadillac stretch limousine']),
        ('chanje', 'chanjetruck', ['Chanje', 'Chanje electric truck', 'Chanje V8100']),
        ('dennis', 'elitenas1', ['"Dennis Eagle" Elite', 'Dennis Eagle truck', 'Dennis Eagle']),
        ('freightliner', 'electric126daycab', ['Freightliner day cab', 'Freightliner Cascadia', 'Freightliner truck']),
        ('korando', 'korandolhd', ['SsangYong Korando', 'KGM Korando', 'SsangYong truck']),
        ('westernstar', '49xrhdchassis', ['"Western Star 49X"', 'Western Star truck', 'Western Star 49X']),
        ('white', 'highcabovershort', ['"White" truck COE', 'White Freightliner', 'White Motor Company truck']),
        # wrong-content picks from round 1
        ('chevrolet', 'hicube', ['"Chevrolet" cutaway van', '"Chevrolet" G30 van', 'Chevrolet Chevy Van']),
        ('chevrolet', 'hearselimocommercialchassis', ['Chevrolet hearse', 'Limo chassis hearse', 'Cadillac hearse limo']),
        ('ford', 'gtmkii', ['"Ford GT MKII"', '"Ford GT Mk II"', 'Ford GT racecar']),
        ('gmc', 's15utility', ['"GMC S15"', '"GMC S-15"', 'GMC Sonoma pickup']),
        ('gmc', 'buschassis', ['GMC truck chassis bus', 'GMC school bus', 'Blue Bird GMC bus']),
        ('bluebird', 'chassisonly', ['Blue Bird bus', 'Blue Bird All American bus', 'Blue Bird chassis']),
        ('hyundai', 'santafexl', ['"Hyundai Santa Fe XL"', 'Hyundai Santa Fe 2019', 'Hyundai Santa Fe']),
        ('nissan', 'roguesport', ['"Nissan Rogue Sport"', 'Nissan Rogue 2017', 'Nissan Rogue SUV']),
        ('nissan', 'sentraclassic', ['"Nissan Sentra" Classic', 'Nissan Sentra B13', 'Nissan Sentra']),
        ('peterbilt', '353', ['Peterbilt 353', 'Peterbilt conventional', 'Peterbilt truck']),
        ('peterbilt', '352', ['Peterbilt 352', 'Peterbilt cab over', 'Peterbilt truck']),
        ('peterbilt', '365', ['Peterbilt 365', 'Peterbilt 357', 'Peterbilt truck']),
        ('kalmar', 'model50', ['Kalmar', 'Kalmar terminal tractor', 'Kalmar truck']),
        ('frontline', 'defenselight', ['Frontline vehicle', 'military light vehicle', 'light tactical vehicle']),
        ('frontline', 'defensemedium', ['Frontline vehicle', 'military medium vehicle', 'MTVR truck']),
        ('international', '4700lowprofile', ['"International 4700"', 'International bus chassis', 'International truck']),
        ('international', 'cof9670', ['"International COF"', 'International cab over truck', 'International CO-9670']),
        ('international', 'fordf450', ['"Ford F-450"', 'Ford F-450 chassis', 'Ford F450 truck']),
        ('nd', 'rt1950', ['RT terminal tractor', 'terminal tractor truck', 'shunting truck']),
        ('nd', 'rt2600', ['terminal tractor truck', 'port terminal tractor', 'airport tractor']),
        ('nd', 'rt3300', ['terminal tractor truck', 'port terminal tractor', 'truck tractor']),
        ('orionbus', 'orionii', ['"Orion" bus', 'Orion II bus', 'NYC Transit Orion bus']),
        ('orionbus', 'orioniiiikarus', ['"Orion Ikarus" bus', 'Orion III bus', 'Ikarus bus']),
        ('orionbus', 'orionv', ['"Orion V" bus', 'Orion bus NYC', 'Orion transit bus']),
        ('orionbus', 'orionvi', ['"Orion VI" bus', 'Orion bus NYC', 'Orion low floor bus']),
        ('oshkosh', 'lightclass6series', ['Oshkosh truck light', 'Oshkosh medium truck', 'Oshkosh']),
        ('oshkosh', 'militaryhemtthetplslvsfmtvseries', ['Oshkosh HEMTT', 'Oshkosh PLS truck', 'Oshkosh FMTV']),
        ('oshkosh', 'oshkoshtrailer', ['Oshkosh truck semi', 'Oshkosh trailer truck', 'Oshkosh heavy truck']),
        ('falcon', 'model3', ['Falcon truck', 'Falcon bus', 'Falcon vehicle']),
        ('falcon', 'model6', ['Falcon truck', 'Falcon bus', 'Falcon vehicle']),
        ('falcon', 'model9', ['Falcon truck', 'Falcon bus', 'Falcon vehicle']),
        ('autocar', 'kmedium', ['Autocar truck', 'Autocar K', 'Autocar']),
        ('autocar', 'kshort', ['Autocar truck', 'Autocar K', 'Autocar']),
        ('byd', 'electrictruckchassis', ['BYD truck electric', 'BYD T3 truck', 'BYD electric truck']),
        ('volvo', 'caboverengineht', ['Volvo FH truck', 'Volvo truck cab', 'Volvo truck']),
        ('volvo', 'caboverenginelt', ['Volvo FM truck', 'Volvo truck cab', 'Volvo truck']),
        ('oldsmobile', 'cutlasscalais', ['"Oldsmobile Cutlass Calais"', 'Oldsmobile Calais', 'Oldsmobile Cutlass']),
        ('oldsmobile', 'cutlasscruiser', ['"Oldsmobile Cutlass Cruiser"', 'Oldsmobile Cutlass wagon', 'Oldsmobile wagon']),
        ('oldsmobile', 'cutlasssalon', ['"Oldsmobile Cutlass Salon"', 'Oldsmobile Cutlass']),
        ('seagrave', 'ladder', ['Seagrave fire truck', 'Seagrave ladder', '"Seagrave" aerial']),
        ('mack', 'rw', ['Mack RW truck', 'Mack truck conventional', 'Mack R model']),
        ('hino', 'l6l7', ['Hino truck L6', 'Hino 500 truck', 'Hino truck']),
        ('lotus', 'turboesprit', ['"Lotus Esprit Turbo"', 'Lotus Esprit S3 Turbo', 'Lotus Esprit']),
        ('bugatti', 'chironsupersport', ['"Chiron Super Sport"', '"Bugatti Chiron" SS', 'Bugatti Chiron']),
        ('maserati', 'tc', ['"Chrysler TC" Maserati', '"TC by Maserati"', 'Chrysler TC']),
    ]

    ok = []
    fails = []
    for brand_key, model_key, queries in redo:
        # locate display name + record
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
            fails.append((brand_key, model_key, 'no-manifest-record'))
            continue
        path = rec.get('path')
        if not path:
            fails.append((brand_key, model_key, 'no-path'))
            continue
        dest = ROOT / path.lstrip('/')

        chosen = None
        chosen_q = None
        reason = 'no-candidates'
        tried = set()
        for q in queries:
            cands = search(q + ' filetype:bitmap')
            if not cands:
                continue
            scored = []
            for c in cands:
                s, err = score_candidate(c, db or brand_key, dv or model_key, used_pages)
                if err == 'page-used':
                    continue
                if s:
                    scored.append(s)
            scored.sort(key=lambda x: x[0], reverse=True)
            for score, mratio, cand in scored:
                if cand['title'] in tried:
                    continue
                tried.add(cand['title'])
                result, err = make_webp(cand, dest, used_digests)
                if result:
                    chosen = (cand, result)
                    chosen_q = q
                    break
                reason = f'{q}::{err}'
            if chosen:
                break
        if not chosen:
            fails.append((db or brand_key, dv or model_key, reason))
            print(f'  FAIL {db or brand_key}::{dv or model_key} {reason}', flush=True)
            continue

        cand, result = chosen
        rec['sourceType'] = 'wikimedia_commons'
        rec['imageSource'] = 'Wikimedia Commons'
        rec['status'] = 'downloaded'
        rec['sourceUrl'] = cand['thumburl']
        rec['sourcePage'] = cand['filepage']
        rec['attribution'] = result['fields'].get('Artist', '')
        rec['license'] = result['license']
        rec['licenseUrl'] = result['fields'].get('LicenseUrl', '')
        rec['description'] = result['fields'].get('ImageDescription', '')
        rec['filePage'] = cand['filepage']
        rec['modification'] = 'Resized to at most 640×440 and converted to WebP'
        rec['sha256'] = result['sha256']
        used_digests.add(result['sha256'])
        used_pages.add(cand['filepage'])

        images[brand_key][model_key] = {
            'path': path,
            'attribution': result['fields'].get('Artist', ''),
            'license': result['license'],
            'filePage': cand['filepage'],
        }
        ok.append((db or brand_key, dv or model_key, chosen_q, cand['title']))
        print(f'  OK   {db or brand_key}::{dv or model_key} [{chosen_q}] <- {cand["title"]}', flush=True)
        write('vehicle-images-manifest.json', manifest)
        save_assets(assets)

    write('vehicle-images-manifest.json', manifest)
    save_assets(assets)
    write('tmp/duplicate-fix-v2-results.json', {'ok': ok, 'fails': fails})
    print(f'DONE ok={len(ok)} fails={len(fails)}', flush=True)
    for f in fails:
        print('   FAILED:', f, flush=True)


if __name__ == '__main__':
    main()