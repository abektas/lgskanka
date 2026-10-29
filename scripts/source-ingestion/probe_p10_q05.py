#!/usr/bin/env python3
"""Inspect p10 q05/q06 boundary to explain the residual 172px tail gap."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
doc = pdfium.PdfDocument(str(SRC))
page = doc[9]
W, H = page.get_size()
tp = page.get_textpage()
rects = []
for i in range(tp.count_rects()):
    l, b, r, t = tp.get_rect(i)
    txt = tp.get_text_bounded(l, b, r, t)
    if txt and txt.strip():
        rects.append((H-float(t), H-float(b), float(l), float(r), txt.strip()))
rects.sort()
print(f"p10 (q05 anchor≈29.6, q06 anchor≈403.3)")
print("--- rects y in [340, 470] (q05 tail / q06 head) ---")
for y0,y1,x0,x1,txt in rects:
    if 340 <= y0 <= 470:
        print(f"  y={y0:6.1f}-{y1:6.1f} x={x0:6.1f}-{x1:6.1f} | {txt[:50]!r}")
print("--- large shapes y in [340, 470] ---")
for obj in page.get_objects():
    if obj.type not in (2,3):
        continue
    try:
        l,b,r,t = obj.get_bounds()
    except Exception:
        continue
    x0,y0,x1,y1 = float(l), H-float(t), float(r), H-float(b)
    if (x1-x0)>=30 and (y1-y0)>=25 and 340<=y0<=470:
        print(f"  SHAPE t={obj.type} x={x0:6.1f}-{x1:6.1f} y={y0:6.1f}-{y1:6.1f}")
doc.close()
