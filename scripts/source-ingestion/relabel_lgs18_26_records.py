#!/usr/bin/env python3
"""Make LGS 18-26 analysis records consistent with the (now year-correct) manifests.

PROBLEM: the manifests used to carry a wrong year inside the question id
(2018..2023 -> "2023", 2024..2025 -> "2025"), so 810 question records had only 270
unique ids. The analyzer keys its done-set on the id, so only the first year of each
id group was ever analysed and those records were stored under the group's wrong id.

METHOD (proof-based, no guessing):
  For every existing record, look up which year-manifest(s) contain that id AND have
  the same `page` as the record. The record's true source year is necessarily in that
  set (its page came from that year's manifest).
    * exactly one match -> PROVEN source year: relabel the record to it and keep it.
    * more than one      -> ambiguous: DROP the record so the analyzer redoes it.
    * zero matches       -> inconsistent: DROP the record.
  Dropping is safe and cheap: the analyzer is resumable, and the crop is untouched.

Usage:
  python3 relabel_lgs18_26_records.py            # dry-run, prints the plan
  python3 relabel_lgs18_26_records.py --apply
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

ROOT = Path("/home/selam/roller/web/lgs-ai-coach/Lgs_18-26")
SUBJECTS = ["turkce", "matematik", "fen-bilimleri", "ingilizce", "din-kulturu", "inkilap-tarihi"]
YEARS = list(range(2018, 2027))
ID_RE = re.compile(r"^(MEB-LGS)-(\d{4})-([A-Z\-]+)-(Q\d{1,3})$")


def build_index():
    """(subject, Qnn) -> {year: page}  and  full_id -> (subject, year, page)."""
    by_qnn, by_id = {}, {}
    for s in SUBJECTS:
        for y in YEARS:
            p = ROOT / f"nuli-{y}-all-subjects-20pt" / s / "manifest.json"
            if not p.exists():
                continue
            man = json.loads(p.read_text(encoding="utf-8"))
            for q in man.get("questions", []):
                qn = q["id"].split("-")[-1]
                by_qnn.setdefault((s, qn), {})[y] = q.get("page")
                by_id[q["id"]] = (s, y, q.get("page"))
    return by_qnn, by_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    by_qnn, by_id = build_index()
    print(f"manifest indeksi: {len(by_id)} benzersiz id")

    kept = relabeled = dropped = total = 0
    per_subject = {}
    for s in SUBJECTS:
        af = ROOT / f"analysis_{s}.jsonl"
        if not af.exists():
            continue
        out = []
        k = rl = dr = 0
        for line in af.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            total += 1
            r = json.loads(line)
            m = ID_RE.match(r["file"])
            if not m:
                dr += 1
                continue
            qn = m.group(4)
            matches = [y for y, pg in by_qnn.get((s, qn), {}).items() if pg == r.get("page")]
            if len(matches) != 1:
                dr += 1
                continue
            year = matches[0]
            new_id = f"{m.group(1)}-{year}-{m.group(3)}-{m.group(4)}"
            if new_id != r["file"]:
                r["legacyId"] = r["file"]
                r["file"] = new_id
                r["examYear"] = year
                rl += 1
            # final consistency assertion
            ent = by_id.get(new_id)
            if ent is None or (ent[2] is not None and r.get("page") is not None and ent[2] != r["page"]):
                dr += 1
                continue
            out.append(json.dumps(r, ensure_ascii=False))
            k += 1
        per_subject[s] = (k, rl, dr)
        if args.apply and out:
            af.write_text("\n".join(out) + "\n", encoding="utf-8")
        kept += k
        relabeled += rl
        dropped += dr

    print(f"\n{'ders':16s} {'kalan':>6s} {'yeniden etiket':>15s} {'silinen':>8s}")
    for s, (k, rl, dr) in per_subject.items():
        print(f"{s:16s} {k:>6} {rl:>15} {dr:>8}")
    print(f"\ntoplam kayıt        : {total}")
    print(f"kalan (kanıtlı)     : {kept}")
    print(f"yeniden etiketlenen : {relabeled}")
    print(f"silinen (yeniden analiz edilecek): {dropped}")
    if not args.apply:
        print("\n(dry-run — yazmak için --apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())