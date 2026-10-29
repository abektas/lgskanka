#!/usr/bin/env python3
"""2015 TALİMATNAME ANALİZİ — kural tabanlı değerlendirme (AI'sız, yerel, tek işçi).

Talimatname kuralı: "AI ile soru DEĞERLENDİRME yok. Analiz kural tabanlı (H1-H7).
OCR/görsel okuma sadece veri çıkarma, puanlama değil. Belirsizse NEEDS_REVIEW."

Bu script yalnız deterministik kurallar uygular — hiçbir model/API çağırmaz.
Mevcut analysis_2015.jsonl kayıtlarına alan EKLER, üzerine yazmaz (önce yedek).

Kural alanları (hepsi questionText + manifest üzerinden):
  - underlineDependent      : "altı çizili / vurgulanan" kalıbı
  - multiStatement          : "I, II, III / hangileri doğrudur" kalıbı
  - negativeWording         : "yanlıştır / olamaz / değildir / eksik"
  - numericOperation        : sayı + "kaç / sonucu / işlem" kalıbı
  - figureRef + figureKind  : "görsel/şekil/tablo/grafik/harita/devre/şema"
  - questionType            : KALIP güçlüyse (Muhakeme / Rutin İşlem / Doğrudan Bilgi),
                              değilse null + rule_uncertain_question_type
  - visualDependency        : none | figure_unverified | data_required
  - status                  : NEEDS_REVIEW (belirsiz/görsel bağımlı) | RULE_ANALYZED

Kullanım:
  python3 analyze_2015_rules.py                 # rapor (dosyaya YAZMAZ)
  python3 analyze_2015_rules.py --apply         # yedek al + analysis_2015.jsonl'e yazar
  python3 analyze_2015_rules.py --samples 3     # raporda örnek kayıt sayısı
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
BASE = REPO / "lgs_18_26"
SUBJECTS = ["turkce", "matematik", "fen-bilimleri", "inkilap-tarihi", "din-kulturu", "ingilizce"]
SUBJECT_NAME = {
    "turkce": "Türkçe", "matematik": "Matematik", "fen-bilimleri": "Fen Bilimleri",
    "inkilap-tarihi": "T.C. İnkılap Tarihi ve Atatürkçülük",
    "din-kulturu": "Din Kültürü ve Ahlak Bilgisi", "ingilizce": "İngilizce",
}

# adim2_questiontext_ocr.py ile AYNI tanım (tutarlılık)
UNDERLINE_RE = re.compile(
    r"alt[ıi]\s*çizili|alt[ıi]nda\s*çizili|vurgulan\w*|kal[ıi]n\s*(yaz|harf)|i[şs]aretli\s*(s[öo]zc[üu]k|c[üu]mle|ifade)",
    re.IGNORECASE)

MULTI_RE = re.compile(
    r"hangileri\s+(doğru|yanlış|eşleş)|hangilerine\s+ulaşıl|ifadelerinden\s+hangileri|"
    r"I,?\s*II,?\s*(III|ve\s+III)|I\.?\s+II\.?\s+III\.", re.IGNORECASE)

NEG_RE = re.compile(r"yanlıştır|olamaz|değildir|eksiktir|düşünülemez|ulaşılamaz", re.IGNORECASE)

NUM_OP_RE = re.compile(
    r"(işleminin\s+sonucu|sonucu\s+kaç|kaçtır\?|kaç\s+(santimetrekare|metre|cm|dm|km|kg|gram|saat|dakika|adet|tane|kişi|para|lira))",
    re.IGNORECASE)

# Karşılaştırma _norm() ile ASCII'ye indirilmiş metin üzerinde yapılır; kalıplar ASCII.
# DİKKAT: "şekillendiren/şekillenme" gibi türetilmiş kelimeler görsel referansı DEĞİLDİR —
# kelime kökü denetimi FIG_BAD_PREFIX ile yapılır (pilotta "sekillendiren" sahte yakalamıştı).
FIG_RE = re.compile(r"\b(gorsel\w*|sekil\w*|tablo\w*|grafik\w*|harita\w*|devre\w*|sema\w*|cizim\w*|resim\w*)")
FIG_BAD_PREFIX = ("sekillen", "sekillendir", "gorselles", "gorsellestir", "devret")
FIG_KIND_BY_PREFIX = (
    ("gorsel", "şekil"), ("sekil", "şekil"), ("cizim", "şekil"),
    ("tablo", "tablo"), ("grafik", "grafik"), ("harita", "harita"),
    ("devre", "devre"), ("sema", "şema"), ("resim", "diğer"),
)

DIRECT_RE = re.compile(r"aşağıdakilerden\s+hangisidir|aşağıdakilerin\s+hangisinde|tanımı|anlamca", re.IGNORECASE)


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c))


def rule_question_type(text: str, multi: bool, neg: bool, num_op: bool):
    """Güçlü kalıp yoksa None — uydurma yok."""
    fired = []
    if multi:
        fired.append("multi_statement_pattern")
        return "Muhakeme", fired
    if neg:
        fired.append("negative_wording_pattern")
        return "Muhakeme", fired
    if num_op:
        fired.append("numeric_operation_pattern")
        return "Rutin İşlem", fired
    if DIRECT_RE.search(text):
        fired.append("direct_knowledge_pattern")
        return "Doğrudan Bilgi", fired
    return None, fired


def rule_figure_kind(text: str):
    t = _norm(text).lower()
    for m in FIG_RE.finditer(t):
        w = m.group(1)
        if any(w.startswith(p) for p in FIG_BAD_PREFIX):
            continue
        for prefix, kind in FIG_KIND_BY_PREFIX:
            if w.startswith(prefix):
                return kind, [f"figure_ref:{m.group(1)}"]
        return "diğer", [f"figure_ref:{m.group(1)}"]
    return None, []


def analyze(rec: dict, topic: str, topic_full: str) -> dict:
    text = rec.get("questionText") or ""
    has_fig = bool(rec.get("hasFigure"))
    fired = []

    underline = bool(UNDERLINE_RE.search(text))
    multi = bool(MULTI_RE.search(text))
    neg = bool(NEG_RE.search(text))
    num_op = bool(NUM_OP_RE.search(text))
    fig_kind, fig_fired = rule_figure_kind(text)
    fired += fig_fired

    qtype, t_fired = rule_question_type(text, multi, neg, num_op)
    fired += t_fired

    warnings = []

    # --- görsel bağımlılık: kural veriyi okuyamaz → belirsizlikte NEEDS_REVIEW ---
    if has_fig and fig_kind:
        visual_dep = "data_required"
        warnings.append("visual_data_not_readable_by_ai")
        fired.append("figure_present+figure_reference")
    elif has_fig and num_op:
        # şekil + sayısal sonuç: sayılar genelde şeklin içindedir, metinde doğrulanamaz
        visual_dep = "data_required"
        warnings.append("visual_data_not_readable_by_ai")
        fired.append("figure_present+numeric_operation")
    elif has_fig:
        visual_dep = "figure_unverified"
        warnings.append("figure_answer_dependency_unverified")
        fired.append("figure_present_no_text_reference")
    elif fig_kind:
        visual_dep = "data_required"  # metin görsel referansı veriyor ama görsel tespit edilmemiş
        warnings.append("visual_data_not_readable_by_ai")
        warnings.append("figure_reference_without_detected_figure")
        fired.append("figure_reference_without_figure")
    else:
        visual_dep = "none"

    if qtype is None:
        warnings.append("rule_uncertain_question_type")

    if visual_dep != "none" or qtype is None:
        status = "NEEDS_REVIEW"
    else:
        status = "RULE_ANALYZED"

    out = dict(rec)  # mevcut alanlar korunur
    out["topic"] = topic
    out["topicFull"] = topic_full
    out["analysisMode"] = "rule_based_v1"
    out["analysisSource"] = "RULES_NO_AI"
    out["analyzedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out["questionType"] = qtype
    out["visualKind"] = fig_kind if fig_kind else "yok"
    out["visualDependency"] = visual_dep
    out["underlineDependent"] = underline or None  # yalnız True ise alan taşı
    out["ruleFlags"] = {
        "multiStatement": multi,
        "negativeWording": neg,
        "numericOperation": num_op,
        "figureReference": bool(fig_kind),
    }
    out["rulesFired"] = fired
    out["analysisWarnings"] = warnings
    out["status"] = status
    out["analysisStatus"] = "RULE_ANALYZED"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="yedek alıp analysis_2015.jsonl'e yaz")
    ap.add_argument("--samples", type=int, default=2, help="raporda örnek kayıt sayısı")
    args = ap.parse_args()

    rows, samples = [], []
    totals = {"soru": 0, "needs_review": 0, "data_required": 0, "underline": 0, "qtype_null": 0}

    for slug in SUBJECTS:
        d = BASE / slug
        ana = d / "analysis_2015.jsonl"
        man = d / "manifest_2015.json"
        if not ana.exists():
            continue
        topics = {}
        if man.exists():
            for q in json.loads(man.read_text(encoding="utf-8"))["questions"]:
                topics[q["id"]] = (q.get("topic") or "-", q.get("topicFull") or q.get("topic") or "-")

        recs = [json.loads(l) for l in ana.open(encoding="utf-8") if l.strip()]
        new = []
        cnt = {"soru": len(recs), "needs_review": 0, "data_required": 0, "underline": 0, "qtype_null": 0}
        for r in recs:
            t, tf = topics.get(r["id"], ("-", "-"))
            a = analyze(r, t, tf)
            a["subject"] = SUBJECT_NAME.get(slug, slug)
            new.append(a)
            if a["status"] == "NEEDS_REVIEW":
                cnt["needs_review"] += 1
            if a["visualDependency"] == "data_required":
                cnt["data_required"] += 1
            if a.get("underlineDependent"):
                cnt["underline"] += 1
            if a["questionType"] is None:
                cnt["qtype_null"] += 1
        rows.append((slug, cnt))
        for k in totals:
            totals[k] += cnt[k]
        samples += new[: args.samples]

        if args.apply:
            bak = BASE / "_yedek_kural_oncesi_20261023" / slug
            bak.mkdir(parents=True, exist_ok=True)
            tgt = bak / "analysis_2015.jsonl"
            if not tgt.exists():
                shutil.copy2(ana, tgt)
            with ana.open("w", encoding="utf-8") as f:
                for a in new:
                    f.write(json.dumps(a, ensure_ascii=False) + "\n")

    print("DERS            SORU  NEEDS_REVIEW  GÖRSEL-BAĞIMLI  ALTI-ÇİZİLİ  TİP-BELİRSİZ")
    for slug, c in rows:
        print(f"{slug:15s} {c['soru']:4d}  {c['needs_review']:12d}  {c['data_required']:14d}  "
              f"{c['underline']:11d}  {c['qtype_null']:13d}")
    print(f"{'TOPLAM':15s} {totals['soru']:4d}  {totals['needs_review']:12d}  {totals['data_required']:14d}  "
          f"{totals['underline']:11d}  {totals['qtype_null']:13d}")
    print()
    print("ÖRNEK KAYITLAR:")
    for a in samples:
        print("-" * 70)
        slim = {k: a[k] for k in ("id", "topic", "questionType", "visualKind", "visualDependency",
                                  "underlineDependent", "ruleFlags", "rulesFired",
                                  "analysisWarnings", "status") if k in a}
        print(json.dumps(slim, ensure_ascii=False, indent=1))
    print("-" * 70)
    print("YAZILDI (yedekli):" if args.apply else "RAPOR — dosyalara YAZILMADI (--apply ile yazılır)")


if __name__ == "__main__":
    main()