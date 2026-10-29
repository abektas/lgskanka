#!/usr/bin/env python3
"""Probe cal01.pdf structure: pages, subjects, answer keys, layout."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
doc = pdfium.PdfDocument(str(SRC))
print(f"cal01.pdf: {len(doc)} pages")
print(f"page size: {doc[0].get_size()}")
print()
print("=== İlk 30 sayfa: ilk 3 satır ===")
for pno in range(min(30, len(doc))):
    page = doc[pno]
    tp = page.get_textpage()
    text = tp.get_text_range()[:200].strip()
    lines = [l.strip() for l in text.split("\n") if l.strip()][:3]
    print(f"  p{pno+1}: {' | '.join(lines)[:110]}")
print()
print("=== İÇİNDEKİLER / CEVAP ANAHTARI sayfaları ===")
for pno in range(len(doc)):
    page = doc[pno]
    tp = page.get_textpage()
    text = tp.get_text_range()[:400].upper()
    for marker in ["İÇİNDEKİLER", "CEVAP ANAHTARI", "ANSWER KEY"]:
        if marker in text:
            print(f"  p{pno+1}: {marker}")
            break
doc.close()
