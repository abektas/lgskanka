#!/usr/bin/env python3

"""
MEBİ LGS Denemeleri — tam kütüphane çıkarımı (12 kitap × 90 soru = 1080).

Kaynak: /home/selam/roller/web/kaynak dosyalar/
  - calısma exra/    → LGS-2,4,5,6,8,9,10,11,12
  - lgs_çalışma_soruları/deneme_sinavi/ → LGS-1,3,7
  (LGS-12 her iki klasörde de var; aynı dosya)

Kırpma: extract_2015_v3 ile aynı anchor-atama + 20pt kenar kuralı.
  Düzeltmeler: merge_drawings (tablo hücreleri), fitz anchor (çakışan metin),
  spanning-çakışma kuralı yalnız figürlere, anchor sıra numarası koruması.

Cevap anahtarı: "Cevap Anahtarı.pdf" — sözel 4 sütun (x-pozisyonuna göre),
sayısal numaralı "N. X" çiftleri.

Kullanım:
  python3 extract_mebi_all.py --probe    # sadece sayfa sınırları + anahtar kontrolü
  python3 extract_mebi_all.py            # tam çıkarım
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pdfplumber
import fitz
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from extract_2015_v3 import (
    page_items,
    find_anchors_merged,
    assign_items,
    trim_ink,
    sha256,
    MARGIN,
    DPI,
    PAGE_W,
    PAGE_H,
    COL,
)

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
ROOT = Path("/home/selam/roller/web/kaynak dosyalar")
OUT = REPO / "_mebi_stage"

BOOK_DIRS = {
    2: ROOT / "calısma exra" / "lgs-2",
    4: ROOT / "calısma exra" / "lgs-4",
    5: ROOT / "calısma exra" / "lgs-5",
    6: ROOT / "calısma exra" / "lgs-6",
    8: ROOT / "calısma exra" / "lgs-8",
    9: ROOT / "calısma exra" / "lgs-9",
    10: ROOT / "calısma exra" / "lgs-10",
    11: ROOT / "calısma exra" / "lgs-11",
    12: ROOT / "calısma exra" / "lgs-12",
}
BOOKS = [2]

# Ders başlığı deseni (regex). Bazı kitaplarda "YABANCI DIL" ASCII yazılmış.
HEADERS = {
    "matematik": [r"^MATEMAT[İI]K\s+TEST[İI]\s*$"],
    "fen-bilimleri": [r"^FEN\s+B[İI]L[İI]MLER[İI]\s+TEST[İI]\s*$"],
    "turkce": [r"^T[ÜU]RK[ÇC]E\s+TEST[İI]\s*$"],
    "inkilap-tarihi": [r"^T\.C\.\s*[İI]NKILAP\s+TAR[İI]H[İI]\s+VE\s+ATAT[ÜU]RK[CÇ][ÜU]L[ÜU]K\s+TEST[İI]\s*$"],
    "din-kulturu": [r"^D[İI]N\s+K[ÜU]LT[ÜU]R[ÜU]\s+VE\s+AHLAK\s+B[İI]LG[İI]S[İI]\s+TEST[İI]\s*$"],
    "ingilizce": [r"^YABANCI\s+D[İI]L\s*\([İI]NG[İI]L[İI]ZCE\)\s+TEST[İI]\s*$"],
}
# Sözel bölüm sırası (PDF içinde)
SOZEL_ORDER = ["turkce", "inkilap-tarihi", "din-kulturu", "ingilizce"]
SAYISAL_ORDER = ["matematik", "fen-bilimleri"]
EXPECTED = {
    "turkce": 20, "matematik": 20, "fen-bilimleri": 20,
    "inkilap-tarihi": 10, "din-kulturu": 10, "ingilizce": 10,
}


def book_files(n: int) -> tuple[Path, Path, Path]:
    d = BOOK_DIRS[n]
    return (d / f"MEBİ LGS-{n} Sayısal.pdf",
            d / f"MEBİ LGS-{n} Sözel.pdf",
            d / f"MEBİ LGS-{n} Cevap Anahtarı.pdf")


def norm_line(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().upper()


def detect_starts(pdf_path: Path, subjects: list[str]) -> dict[str, int]:
    """Her dersin başladığı sayfayı başlık satırından bul (1-tabanlı).
    fitz ile hızlı metin taraması (pdfplumber her sayfada çok yavaş)."""
    starts: dict[str, int] = {}
    doc = fitz.open(str(pdf_path))
    for pi in range(len(doc)):
        text = doc[pi].get_text("text")
        for line in text.split("\n"):
            nl = norm_line(line)
            for subj in subjects:
                if subj in starts:
                    continue
                for pat in HEADERS[subj]:
                    m = re.match(pat, nl)
                    if not m:
                        continue
                    rest = nl[m.end():]
                    # "TESTİ: 20 soru" gibi açıklama satırlarını ele
                    if rest.startswith(":"):
                        continue
                    starts[subj] = pi + 1
                    break
    doc.close()
    return starts


def detect_answer_key_page(pdf_path: Path) -> int | None:
    """PDF sonundaki 'CEVAP ANAHTARI' sayfasını bul (1-tabanlı). Son dersin
    sınırı burası olmalı; aksi halde anahtar sayfası soru sanılır."""
    doc = fitz.open(str(pdf_path))
    try:
        for pi in range(len(doc) - 1, -1, -1):
            if "CEVAP ANAHTARI" in str(doc[pi].get_text("text")).upper():
                return pi + 1
    finally:
        doc.close()
    return None


def parse_answer_key(key_pdf: Path) -> dict[str, dict[int, str]]:
    """MEBİ cevap anahtarı: fitz ile sözel 4 sütun (toleranslı kümeleme),
    sayısal 'N.  X' numaralı çiftler."""
    ak: dict[str, dict[int, str]] = {s: {} for s in EXPECTED}
    doc = fitz.open(str(key_pdf))
    try:
        # --- Sözel: sütunlar, A-D harfleri, x-pozisyonuna göre ---
        if len(doc) > 0:
            items = [(w[0], w[1], w[4]) for w in doc[0].get_text("words")
                     if re.match(r"^[A-D]$", w[4])]
            items.sort(key=lambda z: z[0])
            groups = []
            for x0, top, t in items:
                if groups and x0 - groups[-1][-1][0] <= 12:
                    groups[-1].append((x0, top, t))
                else:
                    groups.append([(x0, top, t)])
            groups.sort(key=lambda g: g[0][0])
            if len(groups) >= 4:
                big = max(groups, key=lambda g: len(g))
                rest = sorted([g for g in groups if g is not big], key=lambda g: g[0][0])
                for i, (_, _, t) in enumerate(sorted(big, key=lambda z: z[1]), 1):
                    ak["turkce"][i] = t
                for subj, g in zip(SOZEL_ORDER[1:], rest[:3]):
                    for i, (_, _, t) in enumerate(sorted(g, key=lambda z: z[1]), 1):
                        ak[subj][i] = t

        # --- Sayısal: "N.  X" numaralı çiftler ---
        if len(doc) > 1:
            words = doc[1].get_text("words")
            rows: dict[int, list] = {}
            for w in words:
                rows.setdefault(round(w[1]), []).append(w)
            pairs: list[tuple[float, int, str]] = []
            for ws in rows.values():
                ws.sort(key=lambda w: w[0])
                for i, w in enumerate(ws):
                    m = re.match(r"^(\d{1,2})\.$", w[4])
                    if not m:
                        continue
                    n = int(m.group(1))
                    if not (1 <= n <= 20):
                        continue
                    if i + 1 < len(ws):
                        let = ws[i + 1][4].strip().upper()
                        if let in "ABCDE" and len(let) == 1:
                            pairs.append((float(w[0]), n, let))
            if pairs:
                xs = sorted(p[0] for p in pairs)
                split = (xs[0] + xs[-1]) / 2
                for x0, n, let in pairs:
                    subj = "matematik" if x0 < split else "fen-bilimleri"
                    if n not in ak[subj]:
                        ak[subj][n] = let
    finally:
        doc.close()
    # Regex'i re.match(r"^[A-D]$\", w[4]) zaten yaptık
    return ak


def extract_subject(pdf_path: Path, slug: str, p_start: int, p_end: int,
                    expected: int, ak: dict, book: int, outdir: Path):
    """Tek dersi kırp. max_n koruması: bölüm yeniden başlarsa (n=1) atlanır,
    ama aynı sayfada iki ayrı soru grubu varsa (ör. LGS-11 Q1-4 hem s3 hem s11)
    ikincisi de alınır — bu yüzden max_n sadece son 5 sayfanın anchor'larını
    kontrol eder, sayfa geçişinde sıfırlanmaz."""
    questions = []
    with pdfplumber.open(pdf_path) as pdf:
        doc = fitz.open(str(pdf_path))
        for pidx in range(p_start - 1, min(p_end, len(pdf.pages))):
            page = pdf.pages[pidx]
            pn = pidx + 1
            pg = doc[pidx]
            all_anchors = [a for a in find_anchors_merged(page, pg)
                           if 1 <= a["n"] <= expected]
            if not all_anchors:
                continue
            # MEBİ testinde bölüm içinde restart yok; detect_starts ile
            # sayfa aralığı doğru verildi. Tüm anchor'lar alınır (aynı
            # sayfada iki sütunda çapraz sırada gelse bile hepsi kullanılır).
            anchors = sorted(all_anchors, key=lambda a: (a["col"], a["top"]))
            vpix = pg.get_pixmap(matrix=fitz.Matrix(100 / 72, 100 / 72))
            vimg = Image.frombytes("RGB", (vpix.width, vpix.height), vpix.samples).convert("L")
            items, footer_cap, header_bottom = page_items(page, vimg, 100 / 72)
            groups = assign_items(items, anchors)

            next_top: dict[int, float | None] = {}
            for col in ("L", "R"):
                ci = [i for i, a in enumerate(anchors) if a["col"] == col]
                ci.sort(key=lambda i: anchors[i]["top"])
                for j, i in enumerate(ci):
                    next_top[i] = anchors[ci[j + 1]]["top"] if j + 1 < len(ci) else None

            for i, a in enumerate(anchors):
                if not groups[i]:
                    continue
                gx0 = min(it["x0"] for it in groups[i])
                gy0 = min(it["top"] for it in groups[i])
                gx1 = max(it["x1"] for it in groups[i])
                gy1 = max(it["bot"] for it in groups[i])
                y0 = max(0.0, gy0 - MARGIN)
                y0 = max(y0, min(header_bottom, gy0 - 1))
                y1 = gy1 + MARGIN
                nt = next_top.get(i)
                if nt is not None:
                    y1 = min(y1, nt - 4)
                y1 = min(y1, footer_cap)
                x0 = max(0.0, gx0 - MARGIN)
                x1 = min(PAGE_W, gx1 + MARGIN)
                if all(it["x1"] <= COL for it in groups[i]):
                    x1 = min(x1, max(COL - 3, gx1))
                elif all(it["x0"] >= COL for it in groups[i]):
                    x0 = max(x0, min(COL + 4, gx0))
                if y1 - y0 < 40 or x1 - x0 < 40:
                    print(f"    SKIP LGS{book} {slug} Q{a['n']} p{pn}: küçük bbox")
                    continue
                pix = pg.get_pixmap(matrix=fitz.Matrix(DPI / 72, DPI / 72))
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                sx, sy = img.width / PAGE_W, img.height / PAGE_H
                crop = img.crop((round(x0 * sx), round(y0 * sy), round(x1 * sx), round(y1 * sy)))
                crop, (Lpx, Tpx, Rpx, Bpx) = trim_ink(
                    crop, (gx0 - x0) * sx, (gy0 - y0) * sy, (gx1 - x0) * sx, (gy1 - y0) * sy)
                x0, y0 = x0 + Lpx / sx, y0 + Tpx / sy
                x1, y1 = x0 + (Rpx - Lpx) / sx, y0 + (Bpx - Tpx) / sy
                fname = f"MEBI-LGS{book}-{slug.upper()}-Q{a['n']:02d}.png"
                out = outdir / slug / fname
                crop.save(out, "PNG")
                ans = ak.get(slug, {}).get(a["n"])
                has_fig = any(not it["text"] for it in groups[i])
                text_words = sorted([it for it in groups[i] if it["text"]],
                                    key=lambda it: (round(it["top"]), it["x0"]))
                qtext = " ".join(it["text"] for it in text_words)
                questions.append({
                    "id": f"MEBI-LGS{book}-{slug.upper()}-Q{a['n']:02d}",
                    "questionNumber": a["n"], "page": pn, "column": a["col"],
                    "representation": "IMAGE_BACKED", "file": fname,
                    "questionText": qtext, "hasFigure": has_fig,
                    "topic": slug, "topicFull": slug,
                    "visual": {
                        "publicPath": f"/study/mebi-lgs{book}-{slug}-q{a['n']:02d}.png",
                        "clipRectPt": {"x0": round(x0, 1), "y0": round(y0, 1),
                                       "x1": round(x1, 1), "y1": round(y1, 1)},
                        "renderDpi": DPI, "authority": "ORIGINAL_MEBI_PDF",
                        "reconstructedFromOcr": False, "assetSha256": sha256(out),
                    },
                    "answer": ans, "status": "NEEDS_REVIEW", "published": True,
                    "subject": slug, "sourceBook": f"MEBI-LGS{book}",
                    "examYear": None,
                })
                max_n = a["n"]
        doc.close()
    return questions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()

    print(f"{'Kitap':6} {'Sayısal(sayfa)':28} {'Sözel(sayfa)':34} {'Anahtar'}")
    print("-" * 100)
    plan = {}
    for b in BOOKS:
        say_path, soz_path, key_path = book_files(b)
        if not say_path.exists() or not soz_path.exists() or not key_path.exists():
            print(f"LGS-{b:<3} EKSİK: {say_path.exists()=} {soz_path.exists()=} {key_path.exists()=}")
            continue
        s_starts = detect_starts(say_path, SAYISAL_ORDER)
        z_starts = detect_starts(soz_path, SOZEL_ORDER)
        ak = parse_answer_key(key_path)
        plan[b] = (say_path, soz_path, s_starts, z_starts, ak)

        def rng(starts, order, total):
            out = []
            for i, s in enumerate(order):
                if s not in starts:
                    out.append(f"{s}:?")
                    continue
                end = starts[order[i + 1]] if i + 1 < len(order) and order[i + 1] in starts else total
                out.append(f"{s}:{starts[s]}-{end}")
            return " ".join(out)

        with fitz.open(str(say_path)) as d:
            nsay = len(d)
        with fitz.open(str(soz_path)) as d:
            nsoz = len(d)
        keyinfo = " ".join(f"{k[:4]}:{len(v)}" for k, v in ak.items())
        print(f"LGS-{b:<3} {rng(s_starts, SAYISAL_ORDER, nsay):28} {rng(z_starts, SOZEL_ORDER, nsoz):34} {keyinfo}")

    if args.probe:
        print("\nProbe bitti.")
        return

    all_q: dict[str, list] = {s: [] for s in EXPECTED}
    for b in BOOKS:
        if b not in plan:
            continue
        say_path, soz_path, s_starts, z_starts, ak = plan[b]
        print(f"\n=== LGS-{b} ===")
        for subj, order, starts, pdf_path in (
            *[(s, SAYISAL_ORDER, s_starts, say_path) for s in SAYISAL_ORDER],
            *[(s, SOZEL_ORDER, z_starts, soz_path) for s in SOZEL_ORDER],
        ):
            if subj not in starts:
                print(f"  {subj}: başlık bulunamadı")
                continue
            idx = order.index(subj)
            if idx + 1 < len(order):
                p_end = starts[order[idx + 1]] - 1  # exclusive: next section start page not included
            else:
                akp = detect_answer_key_page(pdf_path)
                p_end = (akp - 1) if akp else len(pdfplumber.open(pdf_path).pages)
            (OUT / subj).mkdir(parents=True, exist_ok=True)
            qs = extract_subject(pdf_path, subj, starts[subj], p_end,
                                 EXPECTED[subj], ak, b, OUT)
            all_q[subj].extend(qs)
            eksik = [n for n in range(1, EXPECTED[subj] + 1)
                     if n not in {q["questionNumber"] for q in qs}]
            print(f"  {subj:16} {len(qs):2}/{EXPECTED[subj]:2} soru  eksik={eksik or 'yok'}")

    print("\n=== ÖZET ===")
    toplam = 0
    for subj, qs in all_q.items():
        cevapsiz = [q["id"] for q in qs if not q["answer"]]
        print(f"{subj:16} {len(qs):4} soru  cevapsız={len(cevapsiz)}")
        toplam += len(qs)
        man = {
            "manifestVersion": "1.0", "status": "NEEDS_REVIEW", "published": True,
            "source": {"sourceId": "MEBI-LGS-DENEMELERI", "sourceType": "PRACTICE_EXAM",
                       "subject": subj, "period": "2024-2025"},
            "questions": qs,
            "answerKeyCandidates": {str(q["questionNumber"]): q["answer"]
                                    for q in qs if q["answer"]},
            "summary": {"questionsExtracted": len(qs), "expectedQuestions": EXPECTED[subj]},
        }
        (OUT / subj / "manifest_mebi.json").write_text(
            json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (OUT / subj / "answers_mebi.json").write_text(
            json.dumps({q["id"]: q["answer"] for q in qs if q["answer"]},
                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"TOPLAM {toplam} soru -> {OUT}")


if __name__ == "__main__":
    main()