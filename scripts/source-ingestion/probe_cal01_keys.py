#!/usr/bin/env python3
"""Inspect cal01 answer-key pages: p306 (unit) and p320/334/... (exam years)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
doc = pdfium.PdfDocument(str(SRC))

for pno in [306, 320, 334]:
    page = doc[pno-1]
    W, H = page.get_size()
    print(f"\n{'='*72}\np{pno}  size={W:.0f}x{H:.0f}")
    tp = page.get_textpage()
    print("--- FULL TEXT ---")
    print(tp.get_text_range()[:1500])
    print("--- rects (first 25, sorted y,x) ---")
    rects = []
    for i in range(tp.count_rects()):
        l, b, r, t = tp.get_rect(i)
        txt = tp.get_text_bounded(l, b, r, t)
        if txt and txt.strip():
            rects.append((H-float(t), H-float(b), float(l), float(r), txt.strip()))
    rects.sort()
    for y0,y1,x0,x1,txt in rects[:25]:
        print(f"  y={y0:6.1f} x={x0:6.1f} | {txt[:60]!r}")
doc.close()
