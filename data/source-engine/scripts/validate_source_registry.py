import json, sys
from pathlib import Path

p = Path("config/source-registry.json")
data = json.loads(p.read_text(encoding="utf-8"))
errors=[]
for s in data["sources"]:
    if s["type"]=="REAL_LGS" and s.get("year",0)<2018:
        errors.append(f"pre-2018 REAL_LGS: {s['id']}")
    if "official_index_url" not in s:
        errors.append(f"missing official URL: {s['id']}")
if errors:
    print("\n".join(errors)); sys.exit(1)
print(f"OK: {len(data['sources'])} source records")
