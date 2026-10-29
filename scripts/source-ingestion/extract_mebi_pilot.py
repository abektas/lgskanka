#!/usr/bin/env python3
"""
MEBİ LGS-2 Pilot Extractor — her dersten 3-4 farklı tür/sayfada soru kırp.
Nüli QBANK kriterleri: anchor tabanlı atama + 20pt dört yandan kırpma.
extract_2015_v3.py crop fonksiyonlarını yeniden kullanır.
"""
import sys
import json
import re
import hashlib
from pathlib import Path

import pdfplumber
import fitz
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from extract_2015_v3 import (
    page_items,
    find_anchors,
    find_anchors_merged,
    assign_items,
    ink_shrink,
    trim_ink,
    norm_tr,
    MARGIN,
    DPI,
    PAGE_W,
    PAGE_H,
    COL,
    QNUM_RE,
    OPT_RE,
)

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
SRC = Path("/home/selam/roller/web/kaynak dosyalar/calısma exra")
OUT = REPO / "_pilot_mebi_lgs2"

# MEBİ LGS-2 ders sınırları (sayfa no, 1-tabanlı, başlangıç-bitiş)
SUBJECTS = [
    ("matematik",      "MEBİ LGS-2 Sayısal.pdf",  3,  11, 20),
    ("fen-bilimleri",  "MEBİ LGS-2 Sayısal.pdf", 11,  23, 20),
    ("turkce",         "MEBİ LGS-2 Sözel.pdf",    3,   8, 20),
    ("inkilap-tarihi", "MEBİ LGS-2 Sözel.pdf",    9,  12, 10),
    ("din-kulturu",    "MEBİ LGS-2 Sözel.pdf",   13,  15, 10),
    ("ingilizce",      "MEBİ LGS-2 Sözel.pdf",   16,  20, 10),
]

# Pilot: her dersten 3-4 soru, farklı sayfa/türlerde
PILOT_QUESTIONS = {
    "matematik":      {1, 7, 14, 20},
    "fen-bilimleri":  {1, 8, 13, 20},
    "turkce":         {1, 10, 12, 20},
    "inkilap-tarihi": {1, 5, 8, 10},
    "din-kulturu":    {1, 4, 7, 10},
    "ingilizce":      {1, 4, 7, 10},
}

SUBJECT_SLUGS = [s[0] for s in SUBJECTS]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while c := f.read(1 << 20):
            h.update(c)
    return h.hexdigest()


def parse_answer_key():
    """MEBİ cevap anahtarı: sözel x-pozisyonuna göre 4 sütun, sayısal numaralı."""
    ak = {s: {} for s in SUBJECT_SLUGS}

    # Sözel: 4 sütun → Türkçe(20), İnkılap(10), Din(10), İngilizce(10)
    # x0 ≈ 90 → turkce 1-20; x0 ≈ 210 → inkilap 1-10; x0 ≈ 330 → din 1-10; x0 ≈ 450 → ingilizce 1-10
    SOZEL_COLS = {90.0: ("turkce", 20), 210.0: ("inkilap-tarihi", 10),
                  330.0: ("din-kulturu", 10), 450.0: ("ingilizce", 10)}

    # Sayısal: "N.   X" numaralı → matematik 1-20, fen 1-20
    with pdfplumber.open(SRC / "MEBİ LGS-2 Cevap Anahtarı.pdf") as pdf:
        # Sayfa 0: Sözel
        p = pdf.pages[0]
        cols = {}
        for w in p.extract_words() or []:
            t = str(w.get("text", "")).strip()
            if not re.match(r"^[A-D]$", t):
                continue
            x0 = round(float(w["x0"]))
            cols.setdefault(x0, []).append((float(w["top"]), t))
        for x0, entries in cols.items():
            # en yakın kolon anahtarını bul
            key = min(SOZEL_COLS, key=lambda k: abs(k - x0))
            if abs(key - x0) > 15:
                continue
            slug, _ = SOZEL_COLS[key]
            entries.sort()
            for i, (_, let) in enumerate(entries, 1):
                ak[slug][i] = let

        # Sayfa 1: Sayısal (numaralı, iki blok: Matematik sol, Fen sağ)
        if len(pdf.pages) > 1:
            p2 = pdf.pages[1]
            rows = {}
            for w in p2.extract_words() or []:
                rows.setdefault(round(float(w["top"])), []).append(w)
            for ws in rows.values():
                ws.sort(key=lambda w: float(w["x0"]))
                for i, w in enumerate(ws):
                    m = re.match(r"^(\d{1,2})\.$", str(w.get("text", "")).strip())
                    if not m:
                        continue
                    x0 = float(w["x0"])
                    slug = "matematik" if x0 < 300 else "fen-bilimleri"
                    if i + 1 < len(ws):
                        let = str(ws[i + 1].get("text", "")).strip().upper()
                        if let in "ABCDE" and len(let) == 1:
                            ak[slug][int(m.group(1))] = let
    return ak


def extract_subject(pdf_path, slug, p_start, p_end, expected, ak, outdir, only):
    questions, done = [], set()
    with pdfplumber.open(pdf_path) as pdf:
        doc = fitz.open(str(pdf_path))
        for pidx in range(p_start - 1, min(p_end, len(pdf.pages))):
            page = pdf.pages[pidx]
            pn = pidx + 1
            pg = doc[pidx]
            anchors = [a for a in find_anchors_merged(page, pg)
                       if 1 <= a["n"] <= expected and a["n"] not in done]
            if not anchors:
                continue
            vpix = pg.get_pixmap(matrix=fitz.Matrix(100 / 72, 100 / 72))
            vimg = Image.frombytes("RGB", (vpix.width, vpix.height), vpix.samples).convert("L")
            items, footer_cap, header_bottom = page_items(page, vimg, 100 / 72)
            groups = assign_items(items, anchors)

            next_top = {}
            for col in ("L", "R"):
                col_idx = [i for i, a in enumerate(anchors) if a["col"] == col]
                col_idx.sort(key=lambda i: anchors[i]["top"])
                for j, i in enumerate(col_idx):
                    next_top[i] = anchors[col_idx[j + 1]]["top"] if j + 1 < len(col_idx) else None

            for i, a in enumerate(anchors):
                if a["n"] in done or not groups[i]:
                    continue
                if a["n"] not in only:
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
                    print(f"  SKIP Q{a['n']} (küçük bbox)")
                    continue
                pg = doc[pidx]
                pix = pg.get_pixmap(matrix=fitz.Matrix(DPI / 72, DPI / 72))
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                sx, sy = img.width / PAGE_W, img.height / PAGE_H
                crop = img.crop((round(x0 * sx), round(y0 * sy), round(x1 * sx), round(y1 * sy)))
                crop, (Lpx, Tpx, Rpx, Bpx) = trim_ink(
                    crop, (gx0 - x0) * sx, (gy0 - y0) * sy, (gx1 - x0) * sx, (gy1 - y0) * sy
                )
                x0, y0 = x0 + Lpx / sx, y0 + Tpx / sy
                x1, y1 = x0 + (Rpx - Lpx) / sx, y0 + (Bpx - Tpx) / sy
                fname = f"MEBI-LGS2-{slug.upper()}-Q{a['n']:02d}.png"
                out = outdir / slug / fname
                crop.save(out, "PNG")
                ans = ak.get(slug, {}).get(a["n"])
                has_fig = any(not it["text"] for it in groups[i])
                text_words = sorted(
                    [it for it in groups[i] if it["text"]],
                    key=lambda it: (round(it["top"]), it["x0"]),
                )
                qtext = " ".join(it["text"] for it in text_words)
                print(
                    f"  Q{a['n']:02d} p{pn}{a['col']} h={y1-y0:.0f}pt w={x1-x0:.0f}pt "
                    f"bbox=({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f}) fig={has_fig} cevap={ans}"
                )
                questions.append(
                    {
                        "id": f"MEBI-LGS2-{slug.upper()}-Q{a['n']:02d}",
                        "questionNumber": a["n"],
                        "page": pn,
                        "column": a["col"],
                        "representation": "IMAGE_BACKED",
                        "file": fname,
                        "questionText": qtext,
                        "hasFigure": has_fig,
                        "topic": slug,
                        "visual": {
                            "publicPath": f"/exams/mebi-lgs2-{slug}-q{a['n']:02d}.png",
                            "clipRectPt": {
                                "x0": round(x0, 1),
                                "y0": round(y0, 1),
                                "x1": round(x1, 1),
                                "y1": round(y1, 1),
                            },
                            "renderDpi": DPI,
                            "authority": "ORIGINAL_MEBI_PDF",
                            "reconstructedFromOcr": False,
                            "assetSha256": sha256(out),
                        },
                        "answer": ans,
                        "status": "NEEDS_REVIEW",
                        "published": True,
                        "subject": slug,
                        "sourceBook": "MEBI-LGS2",
                    }
                )
                done.add(a["n"])
        doc.close()
    return questions


def main():
    ak = parse_answer_key()
    for s in SUBJECT_SLUGS:
        print(f"cevap {s}: {len(ak.get(s, {}))} adet")

    all_q = {}
    for slug, pdfn, ps, pe, exp in SUBJECTS:
        only = PILOT_QUESTIONS.get(slug, set())
        print(f"\n=== {slug} (hedef: {sorted(only)}) ===")
        (OUT / slug).mkdir(parents=True, exist_ok=True)
        qs = extract_subject(SRC / pdfn, slug, ps, pe, exp, ak, OUT, only)
        all_q[slug] = qs
        man = {
            "manifestVersion": "1.0",
            "status": "NEEDS_REVIEW",
            "published": True,
            "source": {
                "sourceId": "MEBI-LGS2",
                "sourceType": "PRACTICE_EXAM",
                "subject": slug,
                "book": "MEBİ LGS-2 Deneme",
            },
            "questions": qs,
            "answerKeyCandidates": {str(q["questionNumber"]): q["answer"] for q in qs if q["answer"]},
            "summary": {"questionsExtracted": len(qs), "expectedQuestions": exp},
        }
        (OUT / slug / "manifest_mebi_lgs2_pilot.json").write_text(
            json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        eksik = [q["questionNumber"] for q in qs if not q["answer"]]
        print(f"  -> {len(qs)}/{len(only)} pilot soru, cevapsız: {eksik or 'yok'}")

    toplam = sum(len(v) for v in all_q.values())
    print(f"\nPilot bitti: {OUT} — toplam {toplam} soru")
    for slug, qs in all_q.items():
        fig = sum(1 for q in qs if q["hasFigure"])
        print(f"  {slug:16} {len(qs)} soru ({fig} figürlü)")


if __name__ == "__main__":
    main()