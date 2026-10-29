#!/usr/bin/env python3
"""Verify subject composition + layout of the tip_1 source PDFs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları")

for name in ["cal01.pdf", "cal02.pdf", "cal05.pdf", "cal06.pdf"]:
    p = SRC / name
    if not p.exists():
        print(f"{name}: YOK")
        continue
    doc = pdfium.PdfDocument(str(p))
    print(f"\n{'='*60}\n{name}: {len(doc)} sayfa\n{'='*60}")
    # Find TOC page and print it
    for pno in range(min(12, len(doc))):
        page = doc[pno]
        tp = page.get_textpage()
        text = tp.get_text_range()
        if "İÇİNDEKİLER" in text.upper():
            print(f"  İÇİNDEKİLER p{pno+1}:")
            # Print subject-like lines (uppercase, no digits at start)
            for line in text.split("\n"):
                line = line.strip()
                if line and not line[0].isdigit() and len(line) > 3:
                    print(f"    {line[:70]}")
            break
    # Column check on first question page
    for pno in range(6, min(12, len(doc))):
        page = doc[pno]
        tp = page.get_textpage()
        rects = []
        H = page.get_size()[1]
        W = page.get_size()[0]
        for i in range(tp.count_rects()):
            l, b, r, t = tp.get_rect(i)
            txt = tp.get_text_bounded(l, b, r, t)
            if txt and txt.strip():
                rects.append((l, W - l))
        if rects:
            xs = sorted(l for l, _ in rects)
            left = sum(1 for x in xs if x < W/2)
            right = sum(1 for x in xs if x >= W/2)
            print(f"  p{pno+1} dizilim: {len(rects)} rect | sol={left} sag={right} -> {'İKİ SÜTUN' if right > 5 else 'TEK SÜTUN'}")
            break
    doc.close()
