#!/usr/bin/env python3
"""Dump p16 (q17) and p19 (q23) rects to explain the residual bottom space."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
doc = pdfium.PdfDocument(str(SRC))
for pno in [16, 19, 22]:
    page = doc[pno-1]
    W, H = page.get_size()
    tp = page.get_textpage()
    rects = []
    for i in range(tp.count_rects()):
        l, b, r, t = tp.get_rect(i)
        txt = tp.get_text_bounded(l, b, r, t)
        if txt and txt.strip():
            rects.append((H-float(t), H-float(b), float(l), float(r), txt.strip()))
    rects.sort()
    print(f"\n{'='*70}\np{pno} (H={H:.0f}) — son 12 içerik rect'i:")
    for y0, y1, x0, x1, txt in rects[-12:]:
        print(f"  y0={y0:6.1f} y1={y1:6.1f} x0={x0:6.1f} x1={x1:6.1f} | {txt[:50]!r}")
doc.close()
