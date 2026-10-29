#!/usr/bin/env python3
"""cal01 v9 crop trial — shape ownership by vertical CENTER.

v8 defect: a question's crop kept a large blank tail (p10 q05, 172px) because the
NEXT question's figure started ~8pt ABOVE the next question's own text row, so the
figure's top fell inside the previous question's window.

Fix: a page object (image/path) belongs to the question whose anchor interval
contains the object's vertical CENTER:  anchor_i <= center < anchor_{i+1}.
Consequences, both correct:
  * the figure is NOT added to the previous question (its center is below), so
    the previous crop ends at its own last text line;
  * the figure IS added to its own question, and that question's crop TOP is
    extended up to the figure's top (a figure may start above its number).

Text stays windowed by top (unchanged from v5). All earlier fixes retained:
keep the number (x>=12), row-band bottom bound, drop page numbers, page frame
and corner logos excluded, significant-shape size floor.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
OUT = Path("/home/selam/.hermes/cache/scratch/cal01_trial_v9")
DPI = 200
MARGIN_PT = 14.0
FOOTER_PT = 60.0
ROW_TOL = 5.0
LINE_TOL = 0.5
LEFT_KEEP_PT = 12.0
RIGHT_KEEP_PT = 12.0
PAGENUM_ZONE_PT = 70.0
LOGO_ZONE_PT = 95.0
FRAME_FRAC = 0.85
MIN_SHAPE_W = 30.0
MIN_SHAPE_H = 25.0
QRE = re.compile(r"^(\d{1,2})[.)]$")
NUM_ONLY = re.compile(r"^\d{1,3}$")

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

def significant_shapes(page, W, H):
    out = []
    for obj in page.get_objects():
        if obj.type not in (2, 3):
            continue
        try:
            l, b, r, t = obj.get_bounds()
        except Exception:
            continue
        x0, y0, x1, y1 = float(l), H - float(t), float(r), H - float(b)
        w, h = x1 - x0, y1 - y0
        if w < MIN_SHAPE_W or h < MIN_SHAPE_H:
            continue
        if w > FRAME_FRAC * W and h > FRAME_FRAC * H:
            continue
        if y1 < LOGO_ZONE_PT and x1 < LOGO_ZONE_PT:
            continue
        if y0 > H - LOGO_ZONE_PT and x0 > W - LOGO_ZONE_PT:
            continue
        out.append((x0, y0, x1, y1))
    return out

def drop_page_numbers(rects, W, H):
    keep = []
    for r in rects:
        if (r["y0"] > H - PAGENUM_ZONE_PT and NUM_ONLY.fullmatch(r["text"])
                and 0.35 * W < r["x0"] < 0.65 * W):
            continue
        keep.append(r)
    return keep

def leftmost_per_line(rects, tol=4.0):
    leftmost = set()
    lines: list[list[int]] = []
    for idx, r in enumerate(rects):
        for ln in lines:
            if abs(rects[ln[0]]["y0"] - r["y0"]) <= tol:
                ln.append(idx)
                break
        else:
            lines.append([idx])
    for ln in lines:
        leftmost.add(min(ln, key=lambda i: rects[i]["x0"]))
    return leftmost

def anchors(rects, W, H):
    lm = leftmost_per_line(rects)
    out = []
    for idx, r in enumerate(rects):
        if idx not in lm:
            continue
        m = QRE.fullmatch(r["text"])
        if not m:
            continue
        n = int(m.group(1))
        if not 1 <= n <= 90:
            continue
        if r["y0"] > H - FOOTER_PT:
            continue
        if r["x0"] > 60.0:
            continue
        out.append({"num": n, "y0": r["y0"], "x0": r["x0"]})
    out.sort(key=lambda a: a["y0"])
    return out

def row_top(rects, anchor_y):
    band = [r["y0"] for r in rects if abs(r["y0"] - anchor_y) <= ROW_TOL]
    return min(band) if band else anchor_y

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(SRC))
    results = []
    for pno in range(7, 27):
        page = doc[pno-1]
        W, H = page.get_size()
        rects = drop_page_numbers(page_rects(page), W, H)
        shapes = significant_shapes(page, W, H)
        anch = anchors(rects, W, H)
        if not anch:
            print(f"p{pno}: anchor yok")
            continue
        img = page.render(scale=DPI/72).to_pil().convert("RGB")
        sx, sy = img.width/W, img.height/H
        # interval bounds per question for shape ownership
        bounds = [a["y0"] for a in anch] + [H - FOOTER_PT]
        for i, a in enumerate(anch):
            y_from, y_next = bounds[i], bounds[i + 1]
            y_end = (row_top(rects, y_next) - LINE_TOL
                     if i + 1 < len(anch) else H - FOOTER_PT)
            # text: windowed by top
            sel = [r for r in rects if y_from - 1.0 <= r["y0"] < y_end
                   and r["x0"] >= LEFT_KEEP_PT]
            # shapes: owned by vertical center
            own = [s for s in shapes
                   if y_from <= (s[1] + s[3]) / 2 < y_next]
            if not sel and not own:
                continue
            xs0 = [r["x0"] for r in sel] + [s[0] for s in own]
            ys0 = [r["y0"] for r in sel] + [s[1] for s in own]
            xs1 = [r["x1"] for r in sel] + [s[2] for s in own]
            ys1 = [r["y1"] for r in sel] + [s[3] for s in own]
            top = max(0.0, min(min(ys0), a["y0"]) - MARGIN_PT)
            bot = min(max(ys1) + MARGIN_PT, y_end)
            l = max(LEFT_KEEP_PT, min(min(xs0), a["x0"]) - MARGIN_PT)
            r = min(W - RIGHT_KEEP_PT, max(xs1) + MARGIN_PT)
            if bot <= top or r <= l:
                continue
            box = (round(l*sx), round(top*sy), round(r*sx), round(bot*sy))
            fp = OUT / f"cal01_p{pno:03d}_q{a['num']:02d}.png"
            img.crop(box).save(fp, "PNG")
            results.append({"page": pno, "q": a["num"], "file": fp.name,
                            "left": round(l,1), "top": round(top,1),
                            "right": round(r,1), "bottom": round(bot,1),
                            "shapes": len(own)})
    doc.close()
    (OUT / "trial.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"toplam {len(results)} crop -> {OUT}")
    for r in results:
        tag = f" [{r['shapes']} sekil]" if r["shapes"] else ""
        print(f"  p{r['page']:3d} q{r['q']:02d} x={r['left']:5.1f}-{r['right']:5.1f} "
              f"y={r['top']:6.1f}-{r['bottom']:6.1f}{tag}")

if __name__ == "__main__":
    main()
