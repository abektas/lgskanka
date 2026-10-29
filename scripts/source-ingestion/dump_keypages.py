#!/usr/bin/env python3
"""Dump key-page and sample-page rect layouts (top-down y) for parser design."""
import re
import sys
from pathlib import Path

import pypdfium2 as pdfium

BASE = Path("/media/selam/Yeni Birim/Lgs Temel Kaynaklar/lgs_çalışma_soruları/tip_1")

TARGETS = {
    "cal05.pdf": [100, 183, 343, 356, 344, 346, 101, 185],
    "cal01.pdf": [306, 307, 308, 320, 7, 8],
    "cal02.pdf": [291, 292, 306, 7, 8],
    "cal06.pdf": [228, 229, 242, 7, 8],
}


def dump(path: Path, pages: list[int]):
    doc = pdfium.PdfDocument(str(path))
    for pno in pages:
        pg = doc[pno - 1]
        H = pg.get_size()[1]
        tp = pg.get_textpage()
        rects = []
        for i in range(tp.count_rects()):
            l, b, r, t = tp.get_rect(i)
            txt = tp.get_text_bounded(l, b, r, t)
            if not txt.strip():
                continue
            # flip to top-down: y0 = H - top, y1 = H - bottom
            rects.append((round(H - t, 1), round(l, 1), round(r, 1), round(H - b, 1), txt.strip()))
        rects.sort(key=lambda x: (x[0], x[1]))
        print(f"\n===== {path.name} p{pno} ({len(rects)} rects) =====")
        for y0, x0, x1, y1, txt in rects:
            print(f"  y={y0:6.1f}-{y1:6.1f} x={x0:6.1f}-{x1:6.1f} | {txt[:80]!r}")
    doc.close()


for fname, pages in TARGETS.items():
    dump(BASE / fname, pages)
