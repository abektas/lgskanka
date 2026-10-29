#!/usr/bin/env python3
"""exams_by_month altındaki PNG'leri public/exams/ altına kopyala (HTTP'den erişilebilir)."""
import json
import shutil
from pathlib import Path

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
SRC = REPO / "lgs_18_26" / "exams_by_month"
DST = REPO / "public" / "exams"

count = 0
for month_dir in sorted(SRC.iterdir()):
    if not month_dir.is_dir():
        continue
    for sub_dir in sorted(month_dir.iterdir()):
        if not sub_dir.is_dir():
            continue
        manifest = month_dir / f"manifest_{month_dir.name}.json"
        if not manifest.exists():
            continue
        man = json.loads(manifest.read_text(encoding="utf-8"))
        for q in man.get("questions", []):
            src = sub_dir / q["file"]
            if not src.exists():
                continue
            dst = DST / month_dir.name / sub_dir.name / q["file"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(src, dst)
                count += 1

print(f"Kopyalandı: {count} PNG -> public/exams/")
