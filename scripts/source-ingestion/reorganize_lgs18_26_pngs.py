#!/usr/bin/env python3
"""Reorganize LGS 18-26 PNGs, manifests, and answer keys into flat subject folders with unique names.

Source: Lgs_18-26/nuli-{YEAR}-all-subjects-20pt/{SUBJECT}/{q-NN.png or QNN.png}
Target: lgs_18_26/{SUBJECT_SLUG}/MEB-LGS-{YEAR}-{SUBJECT_UPPER}-Q{NN}.png
Also copies manifest.json and answer keys to lgs_18_26/{SUBJECT_SLUG}/
"""
from __future__ import annotations
import json
import shutil
from pathlib import Path

SRC_ROOT = Path("/home/selam/roller/web/lgs-ai-coach/Lgs_18-26")
DST_ROOT = Path("/home/selam/roller/web/lgs-ai-coach/lgs_18_26")  # AYRI KLASÖR: denemeler için

SUBJECT_MAP = {
    "turkce": "TURKCE",
    "matematik": "MATEMATIK",
    "fen-bilimleri": "FEN",
    "ingilizce": "INGILIZCE",
    "din-kulturu": "DIN",
    "inkilap-tarihi": "INKILAP",
}

# Target directories
for slug in SUBJECT_MAP:
    (DST_ROOT / slug).mkdir(parents=True, exist_ok=True)

copied = 0
updated_manifests = 0
manifests_copied = 0

for year in range(2018, 2027):
    for subj_slug, subj_upper in SUBJECT_MAP.items():
        src_dir = SRC_ROOT / f"nuli-{year}-all-subjects-20pt" / subj_slug
        dst_dir = DST_ROOT / subj_slug
        man_file = src_dir / "manifest.json"

        if not src_dir.exists() or not man_file.exists():
            continue

        man = json.loads(man_file.read_text(encoding="utf-8"))

        for q in man.get("questions", []):
            # Source PNG: try multiple patterns (q-01.png, Q01.png, page-XX_q-YY.png)
            qnum = q["questionNumber"]
            src_png = None
            for pattern in (f"q-{qnum:02d}.png", f"Q{qnum:02d}.png", f"page-*_q-{qnum:02d}.png"):
                matches = list(src_dir.glob(pattern))
                if matches:
                    src_png = matches[0]
                    break
            if src_png is None:
                print(f"  UYARI: {year} {subj_slug} Q{qnum} PNG bulunamadı")
                continue

            # Target filename: MEB-LGS-2018-TURKCE-Q01.png
            new_name = f"MEB-LGS-{year}-{subj_upper}-Q{qnum:02d}.png"
            dst_png = dst_dir / new_name

            # Copy
            shutil.copy2(src_png, dst_png)
            copied += 1

            # Update manifest file field
            q["file"] = new_name

        # Write updated manifest to source location
        man_file.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
        updated_manifests += 1

        # Copy manifest to destination folder
        dst_man = dst_dir / f"manifest_{year}.json"
        shutil.copy2(man_file, dst_man)
        manifests_copied += 1

        # Copy answer keys to destination folder (if present in manifest)
        # Handle both formats: answerKeyCandidates (2018-2025) and answer_key (2026)
        answer_keys = None
        if "answerKeyCandidates" in man and man["answerKeyCandidates"]:
            answer_keys = man["answerKeyCandidates"]
        elif "answer_key" in man and man["answer_key"]:
            # 2026 format: list of answers
            answer_keys = {str(i+1): ans for i, ans in enumerate(man["answer_key"])}
        elif "items" in man and man["items"]:
            # 2026 format: each item has answer_key
            answer_keys = {str(item.get("question", i+1)): item.get("answer_key") for i, item in enumerate(man["items"]) if item.get("answer_key")}
        
        if answer_keys:
            ans_file = dst_dir / f"answer_keys_{year}.json"
            ans_file.write_text(json.dumps(answer_keys, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"Kopyalanan PNG: {copied}")
print(f"Güncellenen manifest (kaynak): {updated_manifests}")
print(f"Kopyalanan manifest (hedef): {manifests_copied}")

# Verify
print("\nDoğrulama:")
for subj_slug in SUBJECT_MAP:
    png_count = len(list((DST_ROOT / subj_slug).glob("*.png")))
    man_count = len(list((DST_ROOT / subj_slug).glob("manifest_*.json")))
    ans_count = len(list((DST_ROOT / subj_slug).glob("answer_keys_*.json")))
    print(f"  {subj_slug:20s}: {png_count} PNG, {man_count} manifest, {ans_count} answer key")