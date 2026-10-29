#!/usr/bin/env python3
"""cal01 v3 crop trial — fixes three reported defects.

v2 defects (reported by the user on the first 20 pages):
  1. Question NUMBER cut off on the left. Root cause: bbox() filtered
     r["x0"] > 30, and the number run sits at x0≈29, so it was excluded from
     the bbox and the crop's left edge landed right of the number.
     Fix: include the number (filter x0 > 12 only, to drop page-edge marks).
  2. Two questions in one crop. Root cause: bottom = bbox_y1 + MARGIN_PT could
     overrun into the next question's number when the gap was small.
     Fix: bottom = min(bbox_y1 + MARGIN, next_anchor_y0 - 1.5, H - FOOTER).
  3. Large empty space under a question. Root cause: when bbox() returned None
     the fallback stretched the crop to the page footer.
     Fix: fallback caps at the anchor's own content, never the page footer.

Also: top must never be above the anchor's own number, and the bbox is computed
over the SAME y-window used for the crop so content and bounds agree.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
OUT = Path("/home/selam/.hermes/cache/scratch/cal01_trial_v3")
DPI = 200
MARGIN_PT = 14.0
FOOTER_PT = 60.0
MIN_GAP_PT = 1.5          # keep this much clearance before the next anchor
LEFT_KEEP_PT = 12.0       # drop only true page-edge marks, keep the number (x0≈29)
QRE = re.compile(r"^(\d{1,2})[.)]$")

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
        rects = page_rects(page)
        anch = anchors(rects, W, H)
        if not anch:
            print(f"p{pno}: anchor yok")
            continue
        img = page.render(scale=DPI/72).to_pil().convert("RGB")
        sx, sy = img.width/W, img.height/H
        for i, a in enumerate(anch):
            next_y = anch[i+1]["y0"] if i+1 < len(anch) else H - FOOTER_PT
            bb = content_bbox(rects, a["y0"], next_y, LEFT_KEEP_PT)
            if bb is None:
                # no text content: crop a conservative band from the number
                top = max(0.0, a["y0"] - MARGIN_PT)
                bot = min(next_y - MIN_GAP_PT, a["y0"] + 200.0)
                l, r = max(0.0, a["x0"] - MARGIN_PT), W - MARGIN_PT
            else:
                top = max(0.0, min(bb["y0"], a["y0"]) - MARGIN_PT)
                bot = min(bb["y1"] + MARGIN_PT, next_y - MIN_GAP_PT, H - FOOTER_PT)
                l = max(0.0, min(bb["x0"], a["x0"]) - MARGIN_PT)
                r = min(W, bb["x1"] + MARGIN_PT)
            if bot <= top or r <= l:
                continue
            box = (round(l*sx), round(top*sy), round(r*sx), round(bot*sy))
            fp = OUT / f"cal01_p{pno:03d}_q{a['num']:02d}.png"
            img.crop(box).save(fp, "PNG")
            results.append({"page": pno, "q": a["num"], "file": fp.name,
                            "rect_pt": [round(l,1), round(top,1), round(r,1), round(bot,1)],
                            "anchor_y": round(a["y0"],1), "next_y": round(next_y,1),
                            "content_bottom": round(bb["y1"],1) if bb else None})
    doc.close()
    (OUT / "trial.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"toplam {len(results)} crop -> {OUT}")
    print(f"{'pg':>4} {'q':>3} {'top':>7} {'bot':>7} {'anchorY':>8} {'nextY':>7} {'contBot':>8} {'tailGap':>7}")
    for r in results:
        gap = (r["next_y"] - r["content_bottom"]) if r["content_bottom"] else None
        print(f"{r['page']:>4} {r['q']:>3} {r['rect_pt'][1]:>7} {r['rect_pt'][3]:>7} "
              f"{r['anchor_y']:>8} {r['next_y']:>7} {str(r['content_bottom']):>8} "
              f"{('%.1f' % gap) if gap is not None else 'n/a':>7}")

if __name__ == "__main__":
    main()
