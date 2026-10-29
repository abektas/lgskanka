#!/usr/bin/env python3
"""Which questions actually DEPEND on a figure/table/graph?

For each question crop, look at the page's vector objects and images that fall
inside the crop rect and are big enough to be a real figure (not a rule line or
the page frame). Report counts per topic so the hybrid strategy is grounded in
measurement instead of assumption.
"""
from __future__ import annotations
import json
from pathlib import Path
import pypdfium2 as pdfium

PDF = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/tip_1/tu2_turkce_2023.pdf")
MAN = Path("/home/selam/roller/web/lgs-ai-coach/lgs_çalışma_soruları/turkce/manifest_tu2.json")

MIN_W = 40.0
MIN_H = 40.0
MIN_AREA = 4000.0


def figure_area_in(page, H, rect):
    """Total area of sizeable vector/image objects inside the crop rect."""
    x0, y0, x1, y1 = rect["x0"], rect["y0"], rect["x1"], rect["y1"]
    total = 0.0
    biggest = 0.0
    for obj in page.get_objects():
        if obj.type not in (2, 3):      # 2 = path, 3 = image
            continue
        try:
            l, b, r, t = obj.get_bounds()
        except Exception:
            continue
        ox0, oy0, ox1, oy1 = float(l), H - float(t), float(r), H - float(b)
        w, h = ox1 - ox0, oy1 - oy0
        if w < MIN_W or h < MIN_H:
            continue
        # must sit inside the crop
        if ox0 < x0 - 2 or ox1 > x1 + 2 or oy0 < y0 - 2 or oy1 > y1 + 2:
            continue
        a = w * h
        if a < MIN_AREA:
            continue
        total += a
        biggest = max(biggest, a)
    return total, biggest


def main():
    man = json.loads(MAN.read_text(encoding="utf-8"))
    doc = pdfium.PdfDocument(PDF)
    cache = {}

    per_topic = {}
    rows = []
    for q in man["questions"]:
        p = q["page"]
        if p not in cache:
            pg = doc[p - 1]
            cache[p] = (pg, pg.get_size()[1])
        page, H = cache[p]
        tot = big = 0.0
        for rect in q["clipRectsPt"]:
            t, b = figure_area_in(page, H, rect)
            tot += t
            big = max(big, b)
        # crop area for context
        ca = sum((r["x1"] - r["x0"]) * (r["y1"] - r["y0"]) for r in q["clipRectsPt"])
        ratio = tot / ca if ca else 0
        has_fig = big >= MIN_AREA * 3 or ratio > 0.12
        rows.append((q["id"], q["topic"], has_fig, round(ratio, 3), round(big)))
        d = per_topic.setdefault(q["topic"], [0, 0])
        d[0 if has_fig else 1] += 1

    print(f"{'konu':44s} {'şekilli':>8s} {'metin':>7s}")
    for t, (f, nf) in sorted(per_topic.items()):
        print(f"{t[:44]:44s} {f:>8} {nf:>7}")
    tot_fig = sum(1 for r in rows if r[2])
    print(f"\nTOPLAM: {tot_fig}/{len(rows)} soruda belirgin şekil/tablo/grafik var")
    print("\nşekilli sorulardan örnekler:")
    for r in rows:
        if r[2]:
            print(f"   {r[0]}  {r[1][:34]:34s} oran={r[3]} en_büyük={r[4]}pt²")


if __name__ == "__main__":
    main()