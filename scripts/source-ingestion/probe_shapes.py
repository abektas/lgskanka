#!/usr/bin/env python3
"""Probe p21 (q27) and p26 (q38): text rects vs image/vector objects.

Answer choices on these questions are SHAPES (vectors/images), not text, so a
text-only bbox cuts them off. We need the full page-object bounds.
pypdfium2 API: obj.type (1=text,2=path,3=image,4=shading,5=form),
obj.get_bounds() -> (left, bottom, right, top) in PDF points.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
doc = pdfium.PdfDocument(str(SRC))

for pno in [21, 26]:
    page = doc[pno-1]
    W, H = page.get_size()
    print(f"\n{'='*72}\np{pno}  size={W:.0f}x{H:.0f}")
    tp = page.get_textpage()
    rects = []
    for i in range(tp.count_rects()):
        l, b, r, t = tp.get_rect(i)
        txt = tp.get_text_bounded(l, b, r, t)
        if txt and txt.strip():
            rects.append((H-float(t), H-float(b), float(l), float(r), txt.strip()))
    rects.sort()
    print(f"  text rects: {len(rects)}  (son 6)")
    for y0,y1,x0,x1,txt in rects[-6:]:
        print(f"    y={y0:6.1f}-{y1:6.1f} x={x0:6.1f}-{x1:6.1f} | {txt[:45]!r}")

    imgs, paths = [], []
    counts = {}
    for obj in page.get_objects():
        counts[obj.type] = counts.get(obj.type, 0) + 1
        if obj.type not in (2, 3):
            continue
        try:
            l, b, r, t = obj.get_bounds()
            box = (round(float(l),1), round(H-float(t),1), round(float(r),1), round(H-float(b),1))
        except Exception:
            continue
        (imgs if obj.type == 3 else paths).append(box)
    print(f"  counts: {counts}")
    print(f"  {len(imgs)} image objects:")
    for box in imgs:
        print(f"    IMG  x={box[0]:6.1f}-{box[2]:6.1f} y={box[1]:6.1f}-{box[3]:6.1f}")
    big = [b for b in paths if (b[2]-b[0])>50 or (b[3]-b[1])>35]
    print(f"  {len(paths)} paths, {len(big)} large:")
    for box in sorted(big, key=lambda b: b[1])[:30]:
        print(f"    PATH x={box[0]:6.1f}-{box[2]:6.1f} y={box[1]:6.1f}-{box[3]:6.1f}")
doc.close()
