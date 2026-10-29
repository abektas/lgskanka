#!/usr/bin/env python3
"""Corrected tu2 probe: true anchor count + cross-page continuation measurement."""
from __future__ import annotations
import re
from pathlib import Path
from collections import Counter
import pypdfium2 as pdfium

PDF = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/tip_1/tu2_turkce_2023.pdf")
STANDALONE = re.compile(r"^(\d{1,3})\.$")
PAGENUM = re.compile(r"^\d{1,3}$")

DIVIDER = 297.6
LEFT_MARGIN = (24, 34)
RIGHT_MARGIN = (305, 314)
TOP_CUT = 36.0
BOTTOM_CUT = 770.0


def page_rects(page):
    tp = page.get_textpage()
    H = page.get_size()[1]
    out = []
    for i in range(tp.count_rects()):
        l, b, r, t = tp.get_rect(i)
        txt = tp.get_text_bounded(l, b, r, t)
        if txt and txt.strip():
            out.append({"x0": float(l), "x1": float(r),
                        "y0": H - float(t), "y1": H - float(b),
                        "text": txt.strip()})
    out.sort(key=lambda r: (r["y0"], r["x0"]))
    return out


def is_pagenum(r):
    return bool(PAGENUM.fullmatch(r["text"])) and r["y0"] > 770


def col_of(r):
    if LEFT_MARGIN[0] <= r["x0"] <= LEFT_MARGIN[1]:
        return "L"
    if RIGHT_MARGIN[0] <= r["x0"] <= RIGHT_MARGIN[1]:
        return "R"
    return None


def main():
    doc = pdfium.PdfDocument(PDF)
    n = len(doc)

    total_anchors = 0
    per_page = {}
    continuations = []

    for p in range(7, 192):
        page = doc[p]
        W, H = page.get_size()
        rects = [r for r in page_rects(page) if not is_pagenum(r)]
        body = [r for r in rects if TOP_CUT < r["y0"] < BOTTOM_CUT]
        anchors = []
        for r in body:
            m = STANDALONE.fullmatch(r["text"])
            if not m:
                continue
            c = col_of(r)
            if c:
                anchors.append({"n": int(m.group(1)), "col": c, "y": r["y0"]})
        total_anchors += len(anchors)
        per_page[p + 1] = anchors

        # Continuation check: for each column, is the topmost content rect an anchor?
        for col in ("L", "R"):
            col_rects = [r for r in body if (r["x0"] < DIVIDER if col == "L" else r["x0"] > DIVIDER)]
            col_rects.sort(key=lambda r: r["y0"])
            if not col_rects:
                continue
            top = col_rects[0]
            is_anchor = any(a["col"] == col and abs(a["y"] - top["y0"]) < 3 for a in anchors)
            if not is_anchor:
                continuations.append({"page": p + 1, "col": col,
                                      "text": top["text"][:50]})

    print(f"=== GERÇEK ANCHOR SAYISI (düzeltilmiş filtre) ===")
    print(f"  TOPLAM: {total_anchors}")
    print(f"  Cevap anahtarından beklenen: 582")

    print(f"\n=== SAYFA GEÇİŞİ (continuation) ===")
    print(f"  Devam eden kolon sayısı: {len(continuations)}")
    for c in continuations[:25]:
        print(f"    p{c['page']} {c['col']}: {c['text']!r}")

    # Per-page anchor listing for a range
    print(f"\n=== SAYFA BAZINDA ANCHORLAR (örnek) ===")
    for pnum in [8, 9, 10, 11, 12, 100, 101, 102, 159]:
        a = per_page.get(pnum, [])
        L = ",".join(str(x["n"]) for x in a if x["col"] == "L") or "-"
        R = ",".join(str(x["n"]) for x in a if x["col"] == "R") or "-"
        print(f"  p{pnum:>4}: L=[{L}]  R=[{R}]")


if __name__ == "__main__":
    main()