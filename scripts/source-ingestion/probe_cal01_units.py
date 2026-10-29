#!/usr/bin/env python3
"""Probe cal01 unit boundaries, question numbering, and key page counts."""
import sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
doc = pdfium.PdfDocument(str(SRC))
UNIT_RE = re.compile(r"(\d)\.\s*Ünite", re.IGNORECASE)

# 1) find unit title pages
print("=== 'N. Ünite' geçen sayfalar (ilk 12 satırda) ===")
for pno in range(len(doc)):
    page = doc[pno]
    tp = page.get_textpage()
    head = tp.get_text_range()[:250]
    m = UNIT_RE.search(head)
    if m and pno < 310:
        first = [l.strip() for l in head.split("\n") if l.strip()][:3]
        print(f"  p{pno+1}: unit={m.group(1)} | {' | '.join(first)[:70]}")

print()
print("=== Ünite sınır örnekleri (p7,52,53,120,121,184,185,244,245,274,275,296,297,305) ===")
for pno in [7,52,53,120,121,184,185,244,245,274,275,296,297,305]:
    if pno-1 >= len(doc): continue
    page = doc[pno-1]
    tp = page.get_textpage()
    head = tp.get_text_range()[:200]
    first = [l.strip() for l in head.split("\n") if l.strip()][:3]
    print(f"  p{pno}: {' | '.join(first)[:75]}")
doc.close()
