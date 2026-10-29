#!/usr/bin/env python3
"""cal01 first-20-pages crop trial: single-column question extraction.

Calibration goal: capture the FULL question (stem + figure + all choices),
never just the choices. Crop starts at the question number anchor and ends at
the next question's anchor (or page footer).
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
OUT = Path("/home/selam/.hermes/cache/scratch/cal01_trial")
DPI = 200
MARGIN_PT = 14.0
FOOTER_PT = 60.0
QRE = re.compile(r"^(\d{1,2})[.)]?$")

def page_rects(page):
    tp = page.get_textpage()
    H = page.get_size()[1]
    out = []
    for i in range(tp.count_rects()):
        l, b, r, t = tp.get_rect(i)
        txt = tp.get_text_bounded(l, b, r, t)
        if txt and txt.strip():
            out.append({"x0": float(l), "x1": float(r),
                        "y0": H - float(t), "y1": H - float(b), "text": txt.strip()})
    out.sort(key=lambda r: (r["y0"], r["x0"]))
    return out

def anchors(rects, W, H):
    out = []
    for r in rects:
        m = QRE.fullmatch(r["text"])
        if not m:
            continue
        n = int(m.group(1))
        if not 1 <= n <= 90:
            continue
        if r["y0"] > H - FOOTER_PT:   # skip printed page number
            continue
        if r["x0"] < 90.0:            # single-column: number near left edge
            out.append({"num": n, "y0": r["y0"]})
    return out

def bbox(rects, y_from, y_to):
    sel = [r for r in rects if y_from - 2 <= r["y0"] < y_to and r["x0"] > 30]
    if not sel:
        return None
    return {"x0": min(r["x0"] for r in sel), "y0": min(r["y0"] for r in sel),
            "x1": max(r["x1"] for r in sel), "y1": max(r["y1"] for r in sel)}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(SRC))
    results = []
    for pno in range(7, 27):          # p7..p26
        page = doc[pno-1]
        W, H = page.get_size()
        rects = page_rects(page)
        anch = anchors(rects, W, H)
        if not anch:
            print(f"p{pno}: anchor yok")
            continue
        img = page.render(scale=DPI/72).to_pil().convert("RGB")
        sx, sy = img.width/W, img.height/H
        for i, a in enumerate(anch):
            y_to = anch[i+1]["y0"] if i+1 < len(anch) else H - FOOTER_PT
            bb = bbox(rects, a["y0"], y_to)
            if not bb:
                continue
            # full question: from stem top to last content of the question
            top = max(0.0, bb["y0"] - MARGIN_PT)
            bot = min(H, bb["y1"] + MARGIN_PT)
            l = max(0.0, bb["x0"] - MARGIN_PT)
            r = min(W, bb["x1"] + MARGIN_PT)
            box = (round(l*sx), round(top*sy), round(r*sx), round(bot*sy))
            if box[2] <= box[0] or box[3] <= box[1]:
                continue
            fp = OUT / f"cal01_p{pno:03d}_q{a['num']:02d}.png"
            img.crop(box).save(fp, "PNG")
            results.append({"page": pno, "q": a["num"], "file": fp.name,
                            "rect_pt": [round(l,1), round(top,1), round(r,1), round(bot,1)]})
    doc.close()
    (OUT / "trial.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"toplam {len(results)} crop -> {OUT}")
    for r in results[:40]:
        print(f"  p{r['page']:3d} q{r['q']:02d}  {r['file']}  rect={r['rect_pt']}")

if __name__ == "__main__":
    main()
