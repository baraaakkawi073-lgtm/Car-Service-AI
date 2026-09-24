"""Parse the pasted list of 3,591 missing catalog entries into structured JSON."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TXT = Path(r"C:\Users\B\Downloads\Pasted text (1).txt")
OUT = ROOT / "tmp" / "missing-entries-parsed.json"

entries = {}
for raw in TXT.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line:
        continue
    m = re.match(r"^\*\*(.+?):\*\*\s*(.*?)\s*\.?\s*$", line)
    if not m:
        print(f"SKIP (no match): {line!r}")
        continue
    brand, rest = m.group(1).strip(), m.group(2).strip()
    models = [p.strip() for p in rest.split(";") if p.strip()]
    if not models:
        print(f"SKIP (no models): {line!r}")
        continue
    entries.setdefault(brand, [])
    for mod in models:
        if mod not in entries[brand]:
            entries[brand].append(mod)

total = sum(len(v) for v in entries.values())
print(f"brands: {len(entries)}, entries: {total}")
OUT.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {OUT}")