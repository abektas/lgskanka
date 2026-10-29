#!/usr/bin/env python3
"""Diagnose the three reported crop problems on cal01 p8-p16."""
import sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
QRE = re.compile(r"^(\d{1,2})[.)]$")
QRE_LOOSE = re.compile(r"^(\d{1,2})[.)]?$")

doc = pdfium.PdfDocument(str(SRC))
for pno in [8, 11, 12, 13, 15, 16]:
    page = doc[pno-1]
    W, H = page.get_size()
    tp = page.get_textpage()
    rects = []
    for i in range(tp.count_rects()):
        l, b, r, t = tp.get_rect(i)
        txt = tp.get_text_bounded(l, b, r, t)
        if txt and txt.strip():
            rects.append({"x0": float(l), "x1": float(r),
                          "y0": H-float(t), "y1": H-float(b), "text": txt.strip()})
    rects.sort(key=lambda r: (r["y0"], r["x0"]))
    print(f"\n{'='*70}\np{pno} (H={H:.0f})")
    # show the top-most rects and any 'N.'-looking rect
    print("  İLK 6 rect:")
    for r in rects[:6]:
        print(f"    y={r['y0']:6.1f} x={r['x0']:6.1f} | {r['text'][:60]!r}")
    print("  'N.' adayları:")
    for r in rects:
        m = QRE.fullmatch(r["text"])
        if m and int(m.group(1)) <= 90:
            print(f"    y={r['y0']:6.1f} x={r['x0']:6.1f} | {r['text']!r}")
    print("  SON 4 rect (alt boşluk için):")
    for r in rects[-4:]:
        print(f"    y={r['y0']:6.1f} x={r['x0']:6.1f} | {r['text'][:60]!r}")
doc.close()
