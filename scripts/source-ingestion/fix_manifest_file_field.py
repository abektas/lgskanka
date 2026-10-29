#!/usr/bin/env python3
"""Add 'file' field to all LGS 18-26 manifest questions from visual.publicPath."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path("/home/selam/roller/web/lgs-ai-coach/Lgs_18-26")

for man_file in sorted(ROOT.glob("nuli-*-all-subjects-20pt/*/manifest.json")):
    man = json.loads(man_file.read_text(encoding="utf-8"))
    changed = 0
    for subj in man.get("subjects", []):
        for q in subj.get("questions", []):
            if "file" not in q and "visual" in q and "publicPath" in q["visual"]:
                # Extract filename from path like "/pilot-2025-turkce/q-01.png"
                q["file"] = Path(q["visual"]["publicPath"]).name
                changed += 1
    if changed:
        man_file.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {man_file.relative_to(ROOT)}: {changed} soruya 'file' eklendi")
    else:
        print(f"  {man_file.relative_to(ROOT)}: zaten dolu")

print("Bitti.")