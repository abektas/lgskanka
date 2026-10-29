#!/usr/bin/env python3
"""Annotate English manifest with full page text (no clipRectPt available)."""
import json, sys
from pathlib import Path
import pypdfium2 as pdfium

man_path = Path(sys.argv[1])
pdf_path = Path(sys.argv[2])
man = json.loads(man_path.read_text(encoding='utf-8'))
doc = pdfium.PdfDocument(pdf_path)

cache = {}
n_fig = n_text = 0
for q in man["questions"]:
    p = q["page"]
    if p not in cache:
        pg = doc[p - 1]
        cache[p] = (pg, pg.get_textpage(), pg.get_size()[1], pg.get_size()[0])
    page, tp, H, W = cache[p]
    txt = tp.get_text_bounded(0, 0, W, H)
    txt = txt.replace("\r", " ").strip()
    txt = "\n".join(l.rstrip() for l in txt.splitlines())
    q["questionText"] = txt
    q["hasFigure"] = False  # Can't detect per-question without clipRect
    q["figureRatio"] = 0.0
    if len(txt) >= 80:
        n_text += 1

man_path.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"soru: {len(man['questions'])}")
print(f"  metni çıkan (>=80 karakter): {n_text}")
print(f"  yazıldı: {man_path}")