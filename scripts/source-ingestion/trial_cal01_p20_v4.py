#!/usr/bin/env python3
"""cal01 v4 crop trial — fixes the three reported defects.

Reported defects and root causes:
  1. Question NUMBER cut off (left). v2 filtered bbox runs with x0 > 30; the
     number run sits at x0≈29, so it was dropped and the crop's left edge
     landed to its right. Fix: keep runs with x0 >= LEFT_KEEP_PT (12) only.
  2. TWO questions in one crop. The next question's stem line shares the line
     of the next anchor (stem y0=453.2 vs anchor y0=453.3), so a bbox window
     ending at next_y included it. Fix: end the bbox window at
     next_y - LINE_TOL (1.5pt), not at next_y.
  3. Large EMPTY space under a question. A lone footer page number (bottom
     centre, e.g. '15' at y=781) was counted as content, stretching the bbox
     to the page foot. Fix: drop bottom-centre numeric-only runs before bbox.

The crop's top is the question number's own top (never above it); the bottom
is the last real content line + margin, capped before the next anchor.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
OUT = Path("/home/selam/.hermes/cache/scratch/cal01_trial_v4")
DPI = 200
MARGIN_PT = 14.0
FOOTER_PT = 60.0
LINE_TOL = 1.5            # a line at/after next_anchor-this belongs to the next q
LEFT_KEEP_PT = 12.0       # keep the number (x0≈29); drop only page-edge marks
PAGENUM_ZONE_PT = 70.0    # bottom band where a lone number is the page number
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

def drop_page_numbers(rects, W, H):
    """A lone numeric run in the bottom band near the page centre is the
    printed page number, not content."""
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

def content_bbox(rects, y_from, y_to, x_min):
    sel = [r for r in rects
           if y_from - 1.0 <= r["y0"] < y_to and r["x0"] >= x_min]
    if not sel:
        return None
    return {"x0": min(r["x0"] for r in sel), "y0": min(r["y0"] for r in sel),
            "x1": max(r["x1"] for r in sel), "y1": max(r["y1"] for r in sel)}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(SRC))
    results = []
    for pno in range(7, 27):
        page = doc[pno-1]
        W, H = page.get_size()
        rects = drop_page_numbers(page_rects(page), W, H)
        anch = anchors(rects, W, H)
        if not anch:
            print(f"p{pno}: anchor yok")
            continue
        img = page.render(scale=DPI/72).to_pil().convert("RGB")
        sx, sy = img.width/W, img.height/H
        for i, a in enumerate(anch):
            next_y = anch[i+1]["y0"] if i+1 < len(anch) else H - FOOTER_PT
            y_end = next_y - LINE_TOL
            bb = content_bbox(rects, a["y0"], y_end, LEFT_KEEP_PT)
            if bb is None:
                top = max(0.0, a["y0"] - MARGIN_PT)
                bot = min(y_end, a["y0"] + 160.0)
                l, r = max(0.0, a["x0"] - MARGIN_PT), W - MARGIN_PT
            else:
                top = max(0.0, min(bb["y0"], a["y0"]) - MARGIN_PT)
                bot = min(bb["y1"] + MARGIN_PT, y_end)
                l = max(0.0, min(bb["x0"], a["x0"]) - MARGIN_PT)
                r = min(W, bb["x1"] + MARGIN_PT)
            if bot <= top or r <= l:
                continue
            box = (round(l*sx), round(top*sy), round(r*sx), round(bot*sy))
            fp = OUT / f"cal01_p{pno:03d}_q{a['num']:02d}.png"
            img.crop(box).save(fp, "PNG")
            results.append({"page": pno, "q": a["num"], "file": fp.name,
                            "left": round(l,1), "top": round(top,1),
                            "right": round(r,1), "bottom": round(bot,1),
                            "anchor_y": round(a["y0"],1), "anchor_x": round(a["x0"],1),
                            "next_y": round(next_y,1),
                            "content_bottom": round(bb["y1"],1) if bb else None})
    doc.close()
    (OUT / "trial.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"toplam {len(results)} crop -> {OUT}")
    print(f"{'pg':>4} {'q':>3} {'left':>7} {'top':>7} {'bot':>7} {'anchY':>7} {'nextY':>7} {'contBot':>8}")
    for r in results:
        print(f"{r['page']:>4} {r['q']:>3} {r['left']:>7} {r['top']:>7} {r['bottom']:>7} "
              f"{r['anchor_y']:>7} {r['next_y']:>7} {str(r['content_bottom']):>8}")

if __name__ == "__main__":
    main()
