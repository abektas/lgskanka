import json
from pathlib import Path

def test_registry_policy():
    d=json.loads((Path(__file__).parents[1]/"config/source-registry.json").read_text(encoding="utf-8"))
    years=[x["year"] for x in d["sources"] if x["type"]=="REAL_LGS"]
    assert min(years) >= 2018
    assert "MEB-SAMPLE-ARCHIVE" in [x["id"] for x in d["sources"]]
