#!/usr/bin/env python3
"""cal01 v8 crop trial — text bbox UNION significant shape boxes.

Why not v6/v7:
  * v6 unioned EVERY path → thousands of 1-2pt decorative paths → useless.
  * v7 used a pixel scan over a content x-band → page-edge colour bands leaked
    in and one page's envelope ran past the next question's row.

Fix: take the union of
  (a) the TEXT bbox of the question window (exact, from text rects), and
  (b) the bounding boxes of page objects (image=3 or path=2) whose box is
      "significant" (>= MIN_SHAPE_W x MIN_SHAPE_H pt) and lies in the window,
      excluding the page frame and the corner logos.
A choice-shape is at least ~40x40 pt, so a size floor removes the decorative
noise while keeping every real choice.

Also: the crop's x-band never extends past the content margin, so page-edge
colour bands are excluded by construction.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
OUT = Path("/home/selam/.hermes/cache/scratch/cal01_trial_v8")
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
MIN_SHAPE_W = 30.0        # pt — a real choice/figure is wider than this
MIN_SHAPE_H = 25.0        # pt — and taller than this
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
    """Boxes of image/path objects large enough to be a choice or a figure."""
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

def content_bbox(rects, shapes, y_from, y_to):
    sel = [r for r in rects if y_from - 1.0 <= r["y0"] < y_to
           and r["x0"] >= LEFT_KEEP_PT and r["x1"] <= 10000]
    shp = [s for s in shapes if y_from - 1.0 <= s[1] < y_to]
    if not sel and not shp:
        return None
    xs0 = [r["x0"] for r in sel] + [s[0] for s in shp]
    ys0 = [r["y0"] for r in sel] + [s[1] for s in shp]
    xs1 = [r["x1"] for r in sel] + [s[2] for s in shp]
    ys1 = [r["y1"] for r in sel] + [s[3] for s in shp]
    return {"x0": min(xs0), "y0": min(ys0), "x1": max(xs1), "y1": max(ys1)}

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
        for i, a in enumerate(anch):
            y_end = (row_top(rects, anch[i+1]["y0"]) - LINE_TOL
                     if i + 1 < len(anch) else H - FOOTER_PT)
            bb = content_bbox(rects, shapes, a["y0"], y_end)
            if bb is None:
                continue
            top = max(0.0, min(bb["y0"], a["y0"]) - MARGIN_PT)
            bot = min(bb["y1"] + MARGIN_PT, y_end)
            l = max(LEFT_KEEP_PT, min(bb["x0"], a["x0"]) - MARGIN_PT)
            r = min(W - RIGHT_KEEP_PT, bb["x1"] + MARGIN_PT)
            if bot <= top or r <= l:
                continue
            box = (round(l*sx), round(top*sy), round(r*sx), round(bot*sy))
            fp = OUT / f"cal01_p{pno:03d}_q{a['num']:02d}.png"
            img.crop(box).save(fp, "PNG")
            results.append({"page": pno, "q": a["num"], "file": fp.name,
                            "left": round(l,1), "top": round(top,1),
                            "right": round(r,1), "bottom": round(bot,1),
                            "shapes": len([s for s in shapes if a["y0"]-1 <= s[1] < y_end])})
    doc.close()
    (OUT / "trial.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"toplam {len(results)} crop -> {OUT}")
    for r in results:
        tag = f" [{r['shapes']} sekil]" if r["shapes"] else ""
        print(f"  p{r['page']:3d} q{r['q']:02d} x={r['left']:5.1f}-{r['right']:5.1f} "
              f"y={r['top']:6.1f}-{r['bottom']:6.1f}{tag}")

if __name__ == "__main__":
    main()
