#!/usr/bin/env python3
"""Dump p8 rects around the q1/q2 boundary and the page-number zone."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
doc = pdfium.PdfDocument(str(SRC))
page = doc[7]
W, H = page.get_size()
tp = page.get_textpage()
rects = []
for i in range(tp.count_rects()):
    l, b, r, t = tp.get_rect(i)
    txt = tp.get_text_bounded(l, b, r, t)
    if txt and txt.strip():
        rects.append((H-float(t), H-float(b), float(l), float(r), txt.strip()))
rects.sort()
print(f"p8 H={H:.1f}  (q1 anchor=43.8, q2 anchor=453.3, pageNum~781.2)")
print("\n--- y0 in [430, 480] ---")
for y0, y1, x0, x1, txt in rects:
    if 430 <= y0 <= 480:
        print(f"  y0={y0:6.1f} y1={y1:6.1f} x0={x0:6.1f} x1={x1:6.1f} | {txt[:55]!r}")
print("\n--- y0 in [690, 800] ---")
for y0, y1, x0, x1, txt in rects:
    if 690 <= y0 <= 800:
        print(f"  y0={y0:6.1f} y1={y1:6.1f} x0={x0:6.1f} x1={x1:6.1f} | {txt[:55]!r}")
doc.close()
