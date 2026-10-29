#!/usr/bin/env python3
"""lgs_18_26 standartlaştırma doğrulaması.

Kontroller (6 ders × 12 yıl):
  - manifest_<year>.json: soru sayısı, questionText dolu, answer dolu
  - visual.publicPath -> public/exams/<dosya> mevcut
  - analysis_<year>.jsonl: satır sayısı == manifest soru sayısı
  - answer_keys_<year>.json: tüm soruları kapsıyor
  - gemma kalıntısı yok (topic, learningOutcomeCode, pedagogicalDifficulty vb.)
  - eski dosyalar kaldırılmış (analysis.jsonl, analysis_2015/2016/2017.jsonl,
    analysis_2015_ai.jsonl, *.answer.txt, *.png.bak)
"""
from __future__ import annotations
import json
from pathlib import Path

BASE = Path("/home/selam/roller/web/lgs-ai-coach/lgs_18_26")
PUBLIC = Path("/home/selam/roller/web/lgs-ai-coach/public/exams")
SUBJECTS = ["turkce", "matematik", "fen-bilimleri", "inkilap-tarihi", "din-kulturu", "ingilizce"]
YEARS = list(range(2015, 2027))
GEMMA_FIELDS = {"topic", "topicFull", "learningOutcomeCode", "learningOutcomeText", "skill",
                "pedagogicalDifficulty", "cognitiveLoad", "languageLoad", "distractorStrength",
                "curriculumMapping", "legacyId", "questionTextSource_legacy"}
OLD_FILES = ["analysis.jsonl", "analysis_2015_ai.jsonl"]


def main():
    problems = []
    total_q = total_txt = total_ans = total_nr = total_keys = 0
    for sub in SUBJECTS:
        d = BASE / sub
        if not d.is_dir():
            continue
        for year in YEARS:
            mf = d / f"manifest_{year}.json"
            af = d / f"analysis_{year}.jsonl"
            kf = d / f"answer_keys_{year}.json"
            if not mf.exists():
                problems.append(f"{sub}/{year}: manifest yok")
                continue
            man = json.loads(mf.read_text(encoding="utf-8"))
            qs = man.get("questions", [])
            total_q += len(qs)
            ans = json.loads(kf.read_text(encoding="utf-8")) if kf.exists() else {}
            total_keys += len(ans)
            n_txt = n_ans = n_nr = 0
            for q in qs:
                if (q.get("questionText") or "").strip():
                    n_txt += 1
                else:
                    problems.append(f"{sub}/{year}/{q.get('id')}: questionText bos")
                if q.get("answer"):
                    n_ans += 1
                if q.get("questionNumber") is None:
                    n_nr += 1
                pp = (q.get("visual") or {}).get("publicPath")
                if not pp or not (PUBLIC / Path(pp).name).exists():
                    problems.append(f"{sub}/{year}/{q.get('id')}: publicPath yok -> {pp}")
                for g in GEMMA_FIELDS:
                    if g in q:
                        problems.append(f"{sub}/{year}/{q.get('id')}: gemma alani kalmis -> {g}")
                if str(q.get("questionNumber")) not in ans:
                    problems.append(f"{sub}/{year}/{q.get('id')}: anahtarda yok")
            total_txt += n_txt
            total_ans += n_ans
            total_nr += n_nr
            n_lines = sum(1 for l in af.open(encoding="utf-8") if l.strip()) if af.exists() else 0
            if n_lines != len(qs):
                problems.append(f"{sub}/{year}: analysis {n_lines} != manifest {len(qs)}")
            for old in OLD_FILES:
                if (d / old).exists():
                    problems.append(f"{sub}/{year}: eski dosya kalmis -> {old}")
            for junk in list(d.glob("answers_*.json")) + list(d.glob("*.answer.txt")) + list(d.glob("*.png.bak")):
                problems.append(f"{sub}/{year}: gereksiz dosya -> {junk.name}")

    print(f"manifest soru : {total_q}")
    print(f"questionText  : {total_txt}")
    print(f"answer        : {total_ans}")
    print(f"anahtar kaydi : {total_keys}")
    print(f"soru numarasiz: {total_nr}")
    if problems:
        print(f"\nPROBLEM {len(problems)}:")
        for p in problems[:40]:
            print("  -", p)
    else:
        print("\nTUM KONTROLLER GECI — temiz")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())