#!/usr/bin/env python3
"""MEBI setleri için kural tabanlı kazanım eşleştirme (ADAY — doğrulanmamış).

OCR questionText ↔ MEB TTKB kazanım metinleri arasında kelime benzerliğiyle
aday learningOutcomeCode üretir. Çıktı: analysis_mebi_match.jsonl (ders bazında).
Her kayıt AI_CANDIDATE + NEEDS_REVIEW olarak işaretlenir; kesin doğrulama
insan onayı gerektirir.

Kullanım:
    python3 scripts/source-ingestion/match_mebi_outcomes.py [--threshold 0.12]
"""

import argparse
import json
import math
import re
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_BASE = REPO / "lgs_çalışma_soruları"
CURRICULUM = REPO / "data" / "curriculum" / "meb-2018-grade8-outcomes.json"

SUBJECT_MAP = {
    "turkce": "turkce",
    "matematik": "matematik",
    "fen": "fen",
    "ingilizce": "ingilizce",
    "din-kulturu": "din",
    "inkilap-tarihi": "inkilap",
}

STOPWORDS = set(
    """ve ile veya da de mi mı mu mü bu şu bir iki üç şu kadar için gibi ama fakat
    daha en çok her şey ne hangi nasıl neden niçin olarak olan olur ise ysa diye
    göre karşı doğru yanlış değil dir dir? dır dır tir tır daki daki? nin nın nun
    nün den dan tan ten e a ya ye ye? nda nde ndan nden ndaki
    aşağıdakilerden hangisi hangileri hangisine hangisinde aşağıdakilerden
    soruda soru metin metne göre dayanarak ulaşılır çıkarılır"""
    .split()
)


def norm_token(w: str) -> str:
    """Basit Türkçe normalizasyon: büyük/küçük harf, ek sadeleştirmesi."""
    w = unicodedata.normalize("NFKC", w).lower()
    w = w.translate(str.maketrans("çğıöşü", "cgiosu"))
    w = re.sub(r"[^a-z0-9]", "", w)
    if len(w) > 4:
        for suf in ("lar", "ler", "dir", "dur", "tir", "tur", "miz", "miz", "niz", "ler"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)]
                break
    return w


def tokenize(text: str) -> list:
    toks = []
    for w in re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]+", text or ""):
        t = norm_token(w)
        if len(t) >= 2 and t not in STOPWORDS:
            toks.append(t)
    return toks


def tf(tokens: list) -> dict:
    d = {}
    for t in tokens:
        d[t] = d.get(t, 0) + 1
    return d


def cosine(tf_a: dict, tf_b: dict, idf: dict) -> float:
    num = 0.0
    na = 0.0
    nb = 0.0
    for t, w in tf_a.items():
        iw = idf.get(t, 1.0)
        num += w * iw * tf_b.get(t, 0) * iw
        na += (w * iw) ** 2
    for t, w in tf_b.items():
        iw = idf.get(t, 1.0)
        nb += (w * iw) ** 2
    if na == 0 or nb == 0:
        return 0.0
    return num / math.sqrt(na * nb)


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def build_idf(outcome_tokens: list) -> dict:
    n = len(outcome_tokens)
    df = {}
    for toks in outcome_tokens:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    return {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.12,
                    help="Bu skorun altındaki eşleşmeler LOW_CONFIDENCE olarak işaretlenir")
    args = ap.parse_args()

    cur = json.loads(CURRICULUM.read_text(encoding="utf-8"))

    total = 0
    matched = 0
    low_conf = []
    for folder, subj_key in SUBJECT_MAP.items():
        subj_dir = OUT_BASE / folder
        if not subj_dir.exists():
            continue
        outcome_list = cur["subjects"][subj_key]["outcomes"]
        outcome_docs = [tokenize(o["text"] + " " + (o.get("explanation") or "")) for o in outcome_list]
        outcome_sets = [set(t) for t in outcome_docs]
        idf = build_idf(outcome_docs)
        outcome_tfs = [tf(t) for t in outcome_docs]

        manifest_files = sorted(subj_dir.glob("manifest_mebi_lgs*.json"))
        out_records = []
        for mf in manifest_files:
            if "_pilot" in mf.name:
                continue
            man = json.loads(mf.read_text(encoding="utf-8"))
            for q in man.get("questions", []):
                if q.get("published") is False or q.get("cancelledInSource"):
                    continue
                text = q.get("questionText") or ""
                if not text:
                    continue
                total += 1
                qtoks = tokenize(text)
                qset = set(qtoks)
                qtf = tf(qtoks)

                best = None
                best_score = 0.0
                second = 0.0
                for i, o in enumerate(outcome_list):
                    c = cosine(qtf, outcome_tfs[i], idf)
                    j = jaccard(qset, outcome_sets[i])
                    score = 0.65 * c + 0.35 * j
                    if score > best_score:
                        second = best_score
                        best_score = score
                        best = o
                    elif score > second:
                        second = score

                # İkinci adayla fark küçükse güven düşük (belirsiz eşleşme)
                ambiguity = (best_score - second) < 0.03
                confident = best_score >= args.threshold and not ambiguity
                if confident:
                    matched += 1

                rec = {
                    "file": q.get("file"),
                    "id": q.get("id"),
                    "subject": folder,
                    "sourceBook": q.get("sourceBook"),
                    "questionNumber": q.get("q"),
                    "page": q.get("page"),
                    "learningOutcomeCode": best["code"] if best else None,
                    "learningOutcomeText": best["text"] if best else None,
                    "matchScore": round(best_score, 4),
                    "runnerUpScore": round(second, 4),
                    "matchMethod": "RULE_BASED_CANDIDATE:token-cosine+jaccard",
                    "analysisSource": "AI_CANDIDATE:rule-based-outcome-matcher",
                    "status": "NEEDS_REVIEW" if confident else "NEEDS_REVIEW_LOW_CONFIDENCE",
                    "confidence": "MEDIUM" if confident else "LOW",
                    "published": False,
                    "note": "Aday eşleştirme — insan onayı gerekli. curriculum verification DEĞİLDİR.",
                }
                out_records.append(rec)
                if not confident:
                    low_conf.append(rec)

        out_path = subj_dir / "analysis_mebi_match.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for rec in out_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"{folder}: {len(out_records)} MEBI sorusu eşleştirildi → {out_path.name}")

    print(f"\nToplam MEBI sorusu: {total}, eşleşen: {matched}, düşük güven: {len(low_conf)}")
    low_path = REPO / "logs" / "mebi_match_low_confidence.jsonl"
    low_path.parent.mkdir(exist_ok=True)
    with low_path.open("w", encoding="utf-8") as f:
        for rec in low_conf:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Düşük güvenli liste: {low_path}")


if __name__ == "__main__":
    main()