#!/usr/bin/env python3
"""Fix LGS 18-26 manifest question IDs so each year carries a year-correct unique id.

WHY: the manifests shipped with the year baked wrong into the question id —
2018..2023 all carried `MEB-LGS-2023-<SLUG>-Qnn` and 2024..2025 carried
`MEB-LGS-2025-<SLUG>-Qnn` (only 2026 was right). 810 question records therefore
had only 270 unique ids. The analyzer keys its "already done" set on the id, so
once the 2023-group records existed every 2018-2022 question counted as done and
was never analysed.

WHAT THIS DOES (idempotent, no Ollama needed):
  * rewrites every question id to `MEB-LGS-<folderYear>-<SLUG>-Qnn`
    (SLUG and Qnn are taken from the existing id, so naming stays consistent)
  * keeps the original value in `legacyId` for audit
  * sets `examYear` to the folder year
  * writes a per-year report and asserts ids are unique across the whole corpus

Usage:
  python3 fix_lgs18_26_ids.py            # dry-run, prints the plan
  python3 fix_lgs18_26_ids.py --apply    # writes the manifests
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

ROOT = Path("/home/selam/roller/web/lgs-ai-coach/Lgs_18-26")
SUBJECTS = ["turkce", "matematik", "fen-bilimleri", "ingilizce", "din-kulturu", "inkilap-tarihi"]
YEARS = [str(y) for y in range(2018, 2027)]
ID_RE = re.compile(r"^(MEB-LGS)-(\d{4})-([A-Z\-]+)-(Q\d{1,3})$")


def manifest_path(subj, year):
    return ROOT / f"nuli-{year}-all-subjects-20pt" / subj / "manifest.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the manifests")
    args = ap.parse_args()

    all_ids = {}
    collisions = []
    changed = 0
    per_year = {}

    for subj in SUBJECTS:
        for year in YEARS:
            p = manifest_path(subj, year)
            if not p.exists():
                continue
            man = json.loads(p.read_text(encoding="utf-8"))
            qs = man.get("questions", [])
            if not qs:
                continue
            touched = 0
            for q in qs:
                old = q.get("id") or ""
                m = ID_RE.match(old)
                if not m:
                    # synthesise from position when the id is missing/unparseable
                    slug = {"turkce": "TURKCE", "matematik": "MATEMATIK",
                            "fen-bilimleri": "FEN-BILIMLERI", "ingilizce": "INGILIZCE",
                            "din-kulturu": "DIN-KULTURU", "inkilap-tarihi": "INKILAP-TARIHI"}[subj]
                    new = f"MEB-LGS-{year}-{slug}-Q{int(q.get('questionNumber') or 0):02d}"
                    if new.endswith("Q00"):
                        continue
                else:
                    new = f"{m.group(1)}-{year}-{m.group(3)}-{m.group(4)}"
                if old != new:
                    q["legacyId"] = old
                    q["id"] = new
                    touched += 1
                q["examYear"] = int(year)
                if new in all_ids and all_ids[new] != (subj, year):
                    collisions.append((new, all_ids[new], (subj, year)))
                all_ids[new] = (subj, year)
            per_year[(subj, year)] = (len(qs), touched)
            changed += touched
            if args.apply:
                man["total_questions"] = len(qs)
                p.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{'ders':16s} {'yıl':>5s} {'soru':>5s} {'düzeltilen id':>13s}")
    for (subj, year), (n, t) in sorted(per_year.items()):
        if t:
            print(f"{subj:16s} {year:>5s} {n:>5} {t:>13}")
    print(f"\ntoplam düzeltilen id: {changed}")
    print(f"toplam soru kaydı   : {sum(n for n, _ in per_year.values())}")
    print(f"benzersiz id        : {len(all_ids)}")
    print(f"çakışma             : {len(collisions)}")
    for c in collisions[:10]:
        print("   ", c)
    if not args.apply:
        print("\n(dry-run — yazmak için --apply)")
    return 0 if not collisions else 1


if __name__ == "__main__":
    raise SystemExit(main())