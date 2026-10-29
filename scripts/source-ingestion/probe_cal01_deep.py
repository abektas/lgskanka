#!/usr/bin/env python3
"""Deep structure probe for cal01.pdf."""
import sys, hashlib, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
TIP1 = Path("/media/selam/Yeni Birim/Lgs Temel Kaynaklar/lgs_çalışma_soruları/tip_1/cal01.pdf")

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while c := f.read(1<<20):
            h.update(c)
    return h.hexdigest()

print("=== AYNI DOSYA MI? ===")
print("  yeni:", sha(SRC)[:16], SRC.stat().st_size)
print("  tip1:", sha(TIP1)[:16], TIP1.stat().st_size)
print()

doc = pdfium.PdfDocument(str(SRC))
print(f"=== {len(doc)} sayfa ===")
print()

print("=== p5 ve p6 TAM METİN (İÇİNDEKİLER) ===")
for pno in [5, 6]:
    page = doc[pno-1]
    tp = page.get_textpage()
    text = tp.get_text_range()
    print(f"--- p{pno} ---")
    print(text[:1200])
    print()

print("=== SINAV KAPAĞI ADAYLARI (sayfa ortasında büyük başlık) ===")
for pno in range(290, min(320, len(doc))):
    page = doc[pno]
    tp = page.get_textpage()
    text = tp.get_text_range()[:300].strip()
    lines = [l.strip() for l in text.split("\n") if l.strip()][:3]
    print(f"  p{pno+1}: {' | '.join(lines)[:100]}")

print()
print("=== ÖRNEK SORU SAYFASI p8 (dizilim) ===")
page = doc[7]
tp = page.get_textpage()
print("rects:", tp.count_rects())
text = tp.get_text_range()
print(text[:600])

print()
print("=== ÖRNEK CEVAP ANAHTARI p306 ===")
page = doc[305]
tp = page.get_textpage()
print(tp.get_text_range()[:800])
doc.close()
