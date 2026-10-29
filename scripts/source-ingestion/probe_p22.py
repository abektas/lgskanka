#!/usr/bin/env python3
"""Inspect p22 anchors: why is q29 truncated and where does 'q21' come from?"""
import sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
QRE = re.compile(r"^(\d{1,2})[.)]?$")

doc = pdfium.PdfDocument(str(SRC))
page = doc[21]  # p22
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

print(f"=== p22 ({W:.0f}x{H:.0f}) — 'N.' gibi görünen tüm rect'ler ===")
for r in rects:
    m = QRE.fullmatch(r["text"])
    if m:
        n = int(m.group(1))
        flag = "ANCHOR" if r["x0"] < 90 else "  (sag)"
        print(f"  y={r['y0']:6.1f} x={r['x0']:6.1f} | {r['text']!r:8} n={n:2d} {flag}")

print()
print("=== p22 satır satır (ilk 60 rect) ===")
for r in rects[:60]:
    print(f"  y={r['y0']:6.1f} x={r['x0']:6.1f} | {r['text'][:75]!r}")
doc.close()
