#!/usr/bin/env python3
"""2015 analiz birleştirme — AI katmanı + kural katmanı (talimatname).

Girdi:
  lgs_18_26/<slug>/analysis_2015.jsonl     — çıkarım kayıtları (soru metni, cevap, görsel)
  lgs_18_26/<slug>/analysis_2015_ai.jsonl  — gemma3:4b hibrit analiz (2018-26 ile AYNI şema)

Çıktı: analysis_2015.jsonl — önceki yıllarla aynı alanlar (AI_CANDIDATE + NEEDS_REVIEW)
+ talimatname kural katmanı (underlineDependent, visualDependency, rulesFired).

Politika:
  - Ortak anlamsal alanlarda AI katmanı kazanır (2018-26 ile birebir aynı şema).
  - Kural katmanının kendi alanları korunur (visualDependency, underlineDependent,
    ruleFlags, rulesFired) — denetim izi.
  - status her zaman NEEDS_REVIEW (2018-26 ile aynı; AI çıktısı adaydır, VERIFIED yok).
  - examYear 2015 olarak düzeltilir (analyze_text_mode.py varsayılanı 2023'tür).
  - Yedek: _yedek_kural_oncesi_20261023/<slug>/analysis_2015_premerge.jsonl
"""
from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from analyze_2015_rules import analyze, SUBJECTS, SUBJECT_NAME  # noqa: E402

BASE = Path("/home/selam/roller/web/lgs-ai-coach/lgs_18_26")


def main():
    for slug in SUBJECTS:
        d = BASE / slug
        rec_file = d / "analysis_2015.jsonl"
        ai_file = d / "analysis_2015_ai.jsonl"
        if not rec_file.exists():
            continue
        man = json.loads((d / "manifest_2015.json").read_text(encoding="utf-8"))
        topics = {q["id"]: (q.get("topic") or "-", q.get("topicFull") or "-")
                  for q in man["questions"]}

        ai = {}
        if ai_file.exists():
            for line in ai_file.open(encoding="utf-8"):
                if not line.strip():
                    continue
                r = json.loads(line)
                ai[Path(r["file"]).stem] = r

        bak = BASE / "_yedek_kural_oncesi_20261023" / slug / "analysis_2015_premerge.jsonl"
        bak.parent.mkdir(parents=True, exist_ok=True)
        if not bak.exists():
            shutil.copy2(rec_file, bak)

        out, matched = [], 0
        for line in rec_file.open(encoding="utf-8"):
            if not line.strip():
                continue
            rec = json.loads(line)
            a = analyze(rec, *topics.get(rec["id"], ("-", "-")))
            a["subject"] = SUBJECT_NAME.get(slug, slug)
            air = ai.get(rec["id"])
            if air:
                matched += 1
                rule_warn = a.get("analysisWarnings", [])
                for k, v in air.items():
                    if k in ("file", "page", "answerKeyCandidate", "analysisWarnings"):
                        continue
                    a[k] = v
                a["analysisWarnings"] = list(dict.fromkeys(
                    (air.get("analysisWarnings") or []) + rule_warn))
                a["examYear"] = 2015
                a["q"] = rec.get("questionNumber")
                a["answerKeyCandidate"] = rec.get("answer")
                a["analysisMode"] = (air.get("analysisMode") or "") + "+rules"
                a["analysisStatus"] = "AI_ANALYZED_CANDIDATE"
                a["status"] = "NEEDS_REVIEW"
            out.append(json.dumps(a, ensure_ascii=False) + "\n")

        rec_file.write_text("".join(out), encoding="utf-8")
        print(f"{slug}: {len(out)} kayıt yazıldı | AI katmanı eşleşen: {matched}/{len(out)}")


if __name__ == "__main__":
    main()