#!/usr/bin/env python3
"""
MEBİ LGS-5 tam çıkarıcı (Nüli QBANK).

Kaynak: kaynak dosyalar/calısma exra/lgs-11/{Sözel,Sayısal,Cevap Anahtarı}.pdf
Çıktı: lgs_çalışma_soruları/{ders}/MEBI-LGS11-{DERS}-Q{nn}.png + manifest_mebi_lgs11.json
Şema: uygulamanın servis ettiği manifest şeması (id/file/page/q/unit/...).
extract_2015_v3.py crop fonksiyonları + extract_mebi_pilot.py cevap-anahtarı parser'ı yeniden kullanır.

Kullanım:
  python3 scripts/source-ingestion/extract_mebi_lgs2.py            # tam 90 soru
  python3 scripts/source-ingestion/extract_mebi_lgs2.py --probe    # her dersten 3-4 soru (pilot)
  python3 scripts/source-ingestion/extract_mebi_lgs2.py --subject turkce   # tek ders
"""
import sys
import json
import re
import hashlib
import argparse
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
    MARGIN,
    DPI,
    PAGE_W,
    PAGE_H,
    COL,
)

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
SRC = Path("/home/selam/roller/web/kaynak dosyalar/calısma exra/lgs-11")
OUT = REPO / "lgs_çalışma_soruları"

# (id_slug, folder_slug, pdf_name, page_start, page_end, expected_count)
SUBJECTS = [
    ("turkce",         "turkce",         "MEBİ LGS-11 Sözel.pdf",  3,  11, 20),
    ("inkilap-tarihi", "inkilap-tarihi","MEBİ LGS-11 Sözel.pdf", 12,  15, 10),
    ("din-kulturu",    "din-kulturu",   "MEBİ LGS-11 Sözel.pdf", 16,  19, 10),
    ("ingilizce",      "ingilizce",     "MEBİ LGS-11 Sözel.pdf", 20,  24, 10),
    ("matematik",      "matematik",     "MEBİ LGS-11 Sayısal.pdf", 3,  10, 20),
    ("fen-bilimleri",  "fen",           "MEBİ LGS-11 Sayısal.pdf", 11,  20, 20),
]

PROBE_QUESTIONS = {
    "turkce":         {1, 10, 12, 20},
    "inkilap-tarihi": {1, 5, 8, 10},
    "din-kulturu":    {1, 4, 7, 10},
    "ingilizce":      {1, 4, 7, 10},
    "matematik":      {1, 7, 14, 20},
    "fen-bilimleri":  {1, 8, 13, 20},
}

ID_TO_FOLDER = {s[0]: s[1] for s in SUBJECTS}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def parse_answer_key():
    """MEBİ cevap anahtarı: sözel x-pozisyonuna göre 4 sütun, sayısal numaralı."""
    slugs = [s[0] for s in SUBJECTS]
    ak = {s: {} for s in slugs}

    SOZEL_COLS = {90.0: ("turkce", 20), 210.0: ("inkilap-tarihi", 10),
                  330.0: ("din-kulturu", 10), 450.0: ("ingilizce", 10)}

    with pdfplumber.open(SRC / "MEBİ LGS-11 Cevap Anahtarı.pdf") as pdf:
        # Sayfa 0: Sözel (4 sütun)
        p = pdf.pages[0]
        cols = {}
        for w in p.extract_words() or []:
            t = str(w.get("text", "")).strip()
            if not re.match(r"^[A-D]$", t):
                continue
            x0 = round(float(w["x0"]))
            key = min(SOZEL_COLS, key=lambda k: abs(k - x0))
            if abs(key - x0) > 15:
                continue
            cols.setdefault(key, []).append((float(w["top"]), t))
        for key, entries in cols.items():
            slug, _ = SOZEL_COLS[key]
            entries.sort()
            for i, (_, let) in enumerate(entries, 1):
                ak[slug][i] = let

        # Sayfa 1: Sayısal (numaralı, Matematik sol / Fen sağ)
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


def extract_subject(pdf_path, id_slug, folder_slug, p_start, p_end, expected, ak, outdir, only):
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
            from PIL import Image as _I
            vimg = _I.frombytes("RGB", (vpix.width, vpix.height), vpix.samples).convert("L")
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
                # Sütun filtresi YOK: bir sorunun şıkları/şekilleri her iki sütuna
                # yayılabilir (ör. A,B sol / C,D sağ). assign_items zaten en yakın
                # anchor'a atar. Sahte anchor'lar 'done' filtresiyle elenir.
                if not groups[i]:
                    print(f"  SKIP Q{a['n']} (boş grup)")
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
                # sütun sınırı zorlanmaz (spanning içerik korunur)
                if y1 - y0 < 40 or x1 - x0 < 40:
                    print(f"  SKIP Q{a['n']} (küçük bbox)")
                    continue
                pix = pg.get_pixmap(matrix=fitz.Matrix(DPI / 72, DPI / 72))
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                sx, sy = img.width / PAGE_W, img.height / PAGE_H
                crop = img.crop((round(x0 * sx), round(y0 * sy), round(x1 * sx), round(y1 * sy)))
                crop, (Lpx, Tpx, Rpx, Bpx) = trim_ink(
                    crop, (gx0 - x0) * sx, (gy0 - y0) * sy, (gx1 - x0) * sx, (gy1 - y0) * sy
                )
                x0, y0 = x0 + Lpx / sx, y0 + Tpx / sy
                x1, y1 = x0 + (Rpx - Lpx) / sx, y0 + (Bpx - Tpx) / sy
                fname = f"MEBI-LGS11-{id_slug.upper()}-Q{a['n']:02d}.png"
                out = outdir / folder_slug / fname
                crop.save(out, "PNG")
                ans = ak.get(id_slug, {}).get(a["n"])
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
                        "id": f"MEBI-LGS11-{id_slug.upper()}-Q{a['n']:02d}",
                        "file": fname,
                        "page": pn,
                        "q": a["n"],
                        "unit": None,
                        "unitName": None,
                        "sourceBook": "MEBI_LGS11",
                        "section": "PRACTICE",
                        "examYear": None,
                        "answer": ans,
                        "answerSource": "OFFICIAL_KEY",
                        "status": "NEEDS_REVIEW",
                        "published": True,
                        "cancelledInSource": False,
                        "sha256": sha256(out),
                        "clipRectPt": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                        "column": a["col"],
                        "questionText": qtext,
                        "hasFigure": has_fig,
                        "figureRatio": 0.0,
                    }
                )
                done.add(a["n"])
        doc.close()
    return questions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="her dersten 3-4 soru (pilot)")
    ap.add_argument("--subject", help="tek ders id_slug (örn. turkce)")
    ap.add_argument("--out-dir", help="çıktı klasörü (varsayılan: lgs_çalışma_soruları)")
    args = ap.parse_args()

    global OUT
    if args.out_dir:
        OUT = Path(args.out_dir)

    ak = parse_answer_key()
    for s in [x[0] for x in SUBJECTS]:
        print(f"cevap {s}: {len(ak.get(s, {}))} adet")

    selected = SUBJECTS
    if args.subject:
        selected = [s for s in SUBJECTS if s[0] == args.subject]
        if not selected:
            print("bilinmeyen ders:", args.subject)
            sys.exit(1)

    all_q = {}
    for id_slug, folder_slug, pdfn, ps, pe, exp in selected:
        only = set(range(1, exp + 1))
        if args.probe:
            only = PROBE_QUESTIONS.get(id_slug, {1})
        print(f"\n=== {id_slug} (hedef: {sorted(only)}) ===")
        (OUT / folder_slug).mkdir(parents=True, exist_ok=True)
        qs = extract_subject(SRC / pdfn, id_slug, folder_slug, ps, pe, exp, ak, OUT, only)
        all_q[id_slug] = qs
        matched = sum(1 for q in qs if q["answer"])
        total = len(qs)
        man = {
            "questions": qs,
            "book": "MEBI_LGS11",
            "subject": folder_slug,
            "total_questions": exp if not args.probe else len(only),
            "answerMappingStatus": f"{matched}/{total}",
        }
        man_name = "manifest_mebi_lgs11.json" if not args.probe else "manifest_mebi_lgs11_pilot.json"
        (OUT / folder_slug / man_name).write_text(
            json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        eksik = [q["q"] for q in qs if not q["answer"]]
        print(f"  -> {total}/{len(only)} soru, cevapsız: {eksik or 'yok'}")

    toplam = sum(len(v) for v in all_q.values())
    print(f"\nBitti: {OUT} — toplam {toplam} soru")
    for slug, qs in all_q.items():
        fig = sum(1 for q in qs if q["hasFigure"])
        print(f"  {slug:16} {len(qs)} soru ({fig} figürlü)")


if __name__ == "__main__":
    main()

