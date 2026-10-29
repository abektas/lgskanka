#!/usr/bin/env python3
"""Annotate a manifest with (a) the question text from the PDF text layer and
(b) a hasFigure flag, so the hybrid analyzer knows which questions need the image.

Text comes from the PDF's own text layer via each question's clipRectsPt — no OCR,
and it is exact (verified clean on 582/582 tu2 questions).
hasFigure = a sizeable vector/image object sits inside the crop rect.

Usage: python3 annotate_manifest_text_figures.py <manifest.json> <pdf>
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import pypdfium2 as pdfium

MIN_W, MIN_H, MIN_AREA = 40.0, 40.0, 4000.0


def figure_ratio(page, H, rects):
    ca = sum((r["x1"] - r["x0"]) * (r["y1"] - r["y0"]) for r in rects) or 1.0
    tot = big = 0.0
    for obj in page.get_objects():
        if obj.type not in (2, 3):
            continue
        try:
            l, b, r, t = obj.get_bounds()
        except Exception:
            continue
        ox0, oy0, ox1, oy1 = float(l), H - float(t), float(r), H - float(b)
        w, h = ox1 - ox0, oy1 - oy0
        if w < MIN_W or h < MIN_H:
            continue
        for rect in rects:
            if ox0 < rect["x0"] - 2 or ox1 > rect["x1"] + 2 or oy0 < rect["y0"] - 2 or oy1 > rect["y1"] + 2:
                continue
            a = w * h
            if a >= MIN_AREA:
                tot += a
                big = max(big, a)
            break
    return tot / ca, big


def rects_of(q):
    """Accept both manifest dialects: clipRectsPt (list of dicts) and
    clipRectPt ([x0, y0, x1, y1] as plain numbers)."""
    cr = q.get("clipRectsPt")
    if cr:
        return [{"x0": r["x0"], "y0": r["y0"], "x1": r["x1"], "y1": r["y1"]} for r in cr]
    c = q.get("clipRectPt")
    if c:
        return [{"x0": c[0], "y0": c[1], "x1": c[2], "y1": c[3]}]
    return []


def main():
    man_path = Path(sys.argv[1])
    pdf_path = Path(sys.argv[2])
    man = json.loads(man_path.read_text(encoding="utf-8"))
    doc = pdfium.PdfDocument(pdf_path)

    cache = {}
    n_fig = n_text = 0
    for q in man["questions"]:
        p = q["page"]
        if p not in cache:
            pg = doc[p - 1]
            cache[p] = (pg, pg.get_textpage(), pg.get_size()[1])
        page, tp, H = cache[p]
        rects = rects_of(q)
        txt = ""
        for r in rects:
            txt += tp.get_text_bounded(r["x0"], H - r["y1"], r["x1"], H - r["y0"]) + "\n"
        txt = txt.replace("\r", " ").strip()
        txt = "\n".join(l.rstrip() for l in txt.splitlines())
        q["questionText"] = txt
        ratio, big = figure_ratio(page, H, rects)
        q["hasFigure"] = bool(big >= MIN_AREA * 3 or ratio > 0.12)
        q["figureRatio"] = round(ratio, 3)
        if q["hasFigure"]:
            n_fig += 1
        if len(txt) >= 80:
            n_text += 1

    man_path.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"soru: {len(man['questions'])}")
    print(f"  metni çıkan (>=80 karakter): {n_text}")
    print(f"  şekil içeren (hasFigure)   : {n_fig}")
    print(f"  yazıldı: {man_path}")


if __name__ == "__main__":
    main()