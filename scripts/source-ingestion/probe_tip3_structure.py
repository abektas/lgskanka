#!/usr/bin/env python3
"""Structure probe for tip_3 workbooks."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pypdfium2 as pdfium

INPUT = Path("/media/selam/Yeni Birim/Lgs Temel Kaynaklar/lgs_çalışma_soruları/tip_3")
for pdf in sorted(INPUT.glob("*.pdf")):
    doc = pdfium.PdfDocument(str(pdf))
    print(f"\n{'='*70}\n{pdf.name}: {len(doc)} pages\n{'='*70}")
    # Dump first 15 pages' first 3 lines
    for pno in range(min(15, len(doc))):
        page = doc[pno]
        tp = page.get_textpage()
        text = tp.get_text_range()[:250].strip()
        first = text.split("\n")[0][:70] if text else "(empty)"
        print(f"  p{pno+1}: {first}")
    # Also check TOC
    print("\n  --- searching for İÇİNDEKİLER ---")
    for pno in range(len(doc)):
        page = doc[pno]
        tp = page.get_textpage()
        text = tp.get_text_range()[:600]
        if "İÇİNDEKİLER" in text.upper():
            print(f"  TOC at p{pno+1}:")
            print("   ", text[:500].replace("\r", "").replace("\n", " | "))
            break
    doc.close()
