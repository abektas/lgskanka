#!/usr/bin/env python3
"""lgs_18_26 STANDARTLAŞTIRMA — dots-ocr + kural tabanlı analiz (gemma yok).

Onaylanan hedef durum (6 ders × 12 yıl = 72 manifest, 72 analiz, 12 cevap anahtarı):

  manifest_<year>.json   tek soru alan seti:
      id, questionNumber, page, column, file, examYear, subject, representation,
      published, status, visual (publicPath duzeltilmis), hasFigure, answer,
      questionText (dots-ocr), questionTextSource, ocrAt, underlineDependent,
      questionType, visualKind, visualDependency, ruleFlags, rulesFired, warnings
      cikarilir: topic, topicFull, legacyId

  answer_keys_<year>.json  12 yil icin tek ad/bicim (2015 rename, 2016/2017 uretim)

  analysis_<year>.jsonl    dots-ocr metni + kural alanlari (gemma alanlari YOK)

  kaldirilir (once yedek): analysis.jsonl, analysis_2015/2016/2017.jsonl,
      analysis_2015_ai.jsonl, *.answer.txt, *.png.bak

Sorular PNG olarak kalir (canonical varlik); analiz onlardan uretilir.

Kullanım:
  python3 standardize_lgs18_26.py           # dokunma (rapor + ne yapacagi)
  python3 standardize_lgs18_26.py --apply   # yedek al + uygula
"""
from __future__ import annotations
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from analyze_2015_rules import analyze, SUBJECTS, SUBJECT_NAME  # noqa: E402

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
BASE = REPO / "lgs_18_26"
PUBLIC = REPO / "public" / "exams"
CACHE = REPO / "logs" / "ocr_cache_20261023.jsonl"
BACKUP = BASE / "_yedek_standart_oncesi_20261023"
YEARS = list(range(2015, 2027))
OLD_FILES = ["analysis.jsonl", "analysis_2015_ai.jsonl"]

RULE_KEYS = ("underlineDependent", "questionType", "visualKind", "visualDependency",
             "ruleFlags", "rulesFired", "analysisWarnings", "status")


def load_cache():
    cache = {}
    if CACHE.exists():
        for line in CACHE.open(encoding="utf-8"):
            try:
                d = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            cache[d["key"]] = d
    return cache


def load_answer_key(sub: str, year: int, manifest: dict, d: Path) -> dict:
    """Cevap anahtari: dosya > manifest > .answer.txt (hepsi ayni kaynagin turevi)."""
    for name in (f"answer_keys_{year}.json", f"answers_{year}.json"):
        p = d / name
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v).strip() for k, v in data.items() if str(v).strip()}
    out = {}
    for q in manifest.get("questions", []):
        a = (q.get("answer") or "").strip()
        if a:
            out[str(q.get("questionNumber"))] = a
    if out:
        return out
    for q in manifest.get("questions", []):
        t = d / f"{q['id']}.answer.txt"
        if t.exists():
            v = t.read_text(encoding="utf-8").strip()
            if v:
                out[str(q.get("questionNumber"))] = v
    return out


def public_path(year: int, sub: str, qnum) -> str:
    return f"/exams/{year}-{sub}-q{int(qnum):02d}.png"


def rule_fields(text: str, has_fig: bool) -> dict:
    a = analyze({"questionText": text, "hasFigure": has_fig}, "-", "-")
    out = {k: a[k] for k in RULE_KEYS if k in a}
    out["warnings"] = a["analysisWarnings"]
    return out


def process(sub: str, year: int, cache: dict, apply: bool) -> dict:
    d = BASE / sub
    man = json.loads((d / f"manifest_{year}.json").read_text(encoding="utf-8"))
    answers = load_answer_key(sub, year, man, d)

    questions, missing_ocr, missing_png, missing_ans = [], 0, 0, 0
    for q in man.get("questions", []):
        fn = q.get("file")
        qnum = q.get("questionNumber")
        ocr = cache.get(f"{sub}/{Path(fn).name}") if fn else None
        text = (ocr or {}).get("text", "") if ocr else ""
        if not ocr or not text.strip():
            missing_ocr += 1
        if not fn or not (d / Path(fn).name).exists():
            missing_png += 1

        visual = dict(q.get("visual") or {})
        if fn:
            visual["publicPath"] = public_path(year, sub, qnum)

        rec = {
            "id": q.get("id"),
            "questionNumber": qnum,
            "page": q.get("page"),
            "column": q.get("column"),
            "file": fn,
            "examYear": year,
            "subject": SUBJECT_NAME.get(sub, sub),
            "representation": q.get("representation") or "IMAGE_BACKED",
            "published": q.get("published"),
            "status": None,
            "visual": visual,
            "hasFigure": bool(q.get("hasFigure")),
            "answer": answers.get(str(qnum)),
            "questionText": text,
            "questionTextSource": "dots-ocr",
            "ocrAt": (ocr or {}).get("at"),
        }
        rec.update(rule_fields(text, bool(q.get("hasFigure"))))
        if rec["answer"] is None:
            missing_ans += 1
        questions.append(rec)

    new_man = {
        "manifestVersion": 1.1,
        "standardizedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": man.get("source"),
        "published": man.get("published"),
        "status": man.get("status"),
        "summary": man.get("summary"),
        "total_questions": len(questions),
        "warnings": [],
        "answerKeyCandidates": answers,
        "render": man.get("render"),
        "questions": questions,
    }

    analysis = []
    for r in questions:
        analysis.append({
            "id": r["id"], "file": r["file"], "page": r["page"], "q": r["questionNumber"],
            "examYear": r["examYear"], "subject": r["subject"],
            "answerKeyCandidate": r["answer"], "published": r["published"], "status": r["status"],
            "questionText": r["questionText"], "questionTextSource": "dots-ocr",
            "ocrAt": r["ocrAt"], "questionType": r["questionType"],
            "visualKind": r["visualKind"], "visualDependency": r["visualDependency"],
            "underlineDependent": r["underlineDependent"], "ruleFlags": r["ruleFlags"],
            "rulesFired": r["rulesFired"], "warnings": r["warnings"],
            "analysisMode": "dots_ocr+rules", "analysisSource": "dots-ocr+RULES_NO_AI",
            "analyzedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })

    if apply:
        with (d / f"manifest_{year}.json").open("w", encoding="utf-8") as f:
            json.dump(new_man, f, ensure_ascii=False, indent=1)
        with (d / f"analysis_{year}.jsonl").open("w", encoding="utf-8") as f:
            for a in analysis:
                f.write(json.dumps(a, ensure_ascii=False) + "\n")
        with (d / f"answer_keys_{year}.json").open("w", encoding="utf-8") as f:
            json.dump(answers, f, ensure_ascii=False, indent=0)

    return {"soru": len(questions), "ocr_yok": missing_ocr, "png_yok": missing_png,
            "cevap_yok": missing_ans, "cevap_sayisi": len(answers)}


def backup():
    BACKUP.mkdir(parents=True, exist_ok=True)
    for sub in SUBJECTS:
        d = BASE / sub
        if not d.is_dir():
            continue
        tgt = BACKUP / sub
        tgt.mkdir(parents=True, exist_ok=True)
        for p in list(d.glob("manifest_*.json")) + list(d.glob("answer*.json")) \
                + list(d.glob("analysis*.jsonl")) + list(d.glob("*.answer.txt")) \
                + list(d.glob("*.png.bak")):
            if not (tgt / p.name).exists():
                shutil.copy2(p, tgt / p.name)


def cleanup():
    for sub in SUBJECTS:
        d = BASE / sub
        if not d.is_dir():
            continue
        for name in OLD_FILES:
            p = d / name
            if p.exists():
                p.unlink()
        for p in list(d.glob("answers_*.json")) + list(d.glob("*.answer.txt")) + list(d.glob("*.png.bak")):
            p.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    cache = load_cache()
    ocr_ok = sum(1 for v in cache.values() if v.get("status") == "ok")
    print(f"OCR cache: {ocr_ok} ok / 1080 hedef")
    print("DERS            YIL   SORU  OCR-YOK  CEVAP-YOK  ANAHTAR")
    tot = {"soru": 0, "ocr_yok": 0, "cevap_yok": 0}
    for sub in SUBJECTS:
        for year in YEARS:
            d = BASE / sub
            if not (d / f"manifest_{year}.json").exists():
                continue
            r = process(sub, year, cache, args.apply)
            print(f"{sub:16s} {year}  {r['soru']:5d}  {r['ocr_yok']:6d}  {r['cevap_yok']:9d}  {r['cevap_sayisi']:7d}")
            tot["soru"] += r["soru"]
            tot["ocr_yok"] += r["ocr_yok"]
            tot["cevap_yok"] += r["cevap_yok"]
    print(f"{'TOPLAM':16s}      {tot['soru']:5d}  {tot['ocr_yok']:6d}  {tot['cevap_yok']:9d}")
    if args.apply:
        backup()
        cleanup()
        print(f"YAZILDI. Yedek: {BACKUP}")
    else:
        print("RAPOR — uygulanmadi (--apply ile uygulanir, once yedek alinir)")


if __name__ == "__main__":
    main()