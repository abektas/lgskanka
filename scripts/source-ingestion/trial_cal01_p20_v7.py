#!/usr/bin/env python3
"""cal01 v7 crop trial — pixel-based content envelope (shape-aware).

v6 defect: enumerating page objects caught thousands of tiny decorative paths
(p26 q38 → 2747 "shapes"), so object-union bboxes were unusable.

Root problem restated: the answer choices of some questions are drawn as
images/vectors, not text, so ANY text-only bbox cuts them off.

Robust fix: scan the RENDERED page pixels inside the question's y-window and a
content x-band (excluding page decoration at the far left/right edges), and take
the dark-pixel envelope. This captures text, figures, tables AND shape choices
uniformly. Margins are applied to that envelope.

Kept from v5/v6: keep the question number (content band starts ~12pt), row-band
bottom bound before the next question, drop bottom-centre page numbers.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
OUT = Path("/home/selam/.hermes/cache/scratch/cal01_trial_v7")
SCAN_DPI = 150          # scan resolution (crop is rendered separately at DPI)
DPI = 200
MARGIN_PT = 14.0
FOOTER_PT = 60.0
ROW_TOL = 5.0
LINE_TOL = 0.5
LEFT_BAND_PT = 12.0     # content x-band left edge (keeps the number at ~29)
RIGHT_BAND_PT = 12.0    # drop page-edge decoration on the right
PAGENUM_ZONE_PT = 70.0
DARK = 205              # grayscale threshold for "ink"
MIN_INK = 2             # a row/col needs this many dark px to count
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

def ink_envelope(gray, scale, W, H, y_from, y_to):
    """Dark-pixel envelope (PDF pt) inside y-window and the content x-band."""
    px = gray.load()
    gw, gh = gray.size
    x_lo = int(LEFT_BAND_PT * scale)
    x_hi = int((W - RIGHT_BAND_PT) * scale)
    y_lo = max(0, int(y_from * scale))
    y_hi = min(gh, int(y_to * scale))
    top = bot = left = right = None
    for y in range(y_lo, y_hi):
        cnt = 0
        row_l = row_r = None
        for x in range(x_lo, x_hi, 2):
            if px[x, y] < DARK:
                cnt += 1
                if row_l is None:
                    row_l = x
                row_r = x
        if cnt >= MIN_INK:
            if top is None:
                top = y
            bot = y
            if row_l is not None:
                left = row_l if left is None else min(left, row_l)
                right = row_r if right is None else max(right, row_r)
    if top is None:
        return None
    return {"x0": left / scale, "y0": top / scale,
            "x1": right / scale, "y1": (bot + 1) / scale}

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
        scan = page.render(scale=SCAN_DPI/72).to_pil().convert("L")
        sscale = scan.width / W
        img = page.render(scale=DPI/72).to_pil().convert("RGB")
        sx, sy = img.width/W, img.height/H
        for i, a in enumerate(anch):
            y_end = (row_top(rects, anch[i+1]["y0"]) - LINE_TOL
                     if i + 1 < len(anch) else H - FOOTER_PT)
            env = ink_envelope(scan, sscale, W, H, a["y0"], y_end)
            if env is None:
                continue
            top = max(0.0, min(env["y0"], a["y0"]) - MARGIN_PT)
            bot = min(env["y1"] + MARGIN_PT, y_end)
            l = max(0.0, min(env["x0"], a["x0"]) - MARGIN_PT)
            r = min(W, env["x1"] + MARGIN_PT)
            if bot <= top or r <= l:
                continue
            box = (round(l*sx), round(top*sy), round(r*sx), round(bot*sy))
            fp = OUT / f"cal01_p{pno:03d}_q{a['num']:02d}.png"
            img.crop(box).save(fp, "PNG")
            results.append({"page": pno, "q": a["num"], "file": fp.name,
                            "left": round(l,1), "top": round(top,1),
                            "right": round(r,1), "bottom": round(bot,1)})
    doc.close()
    (OUT / "trial.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"toplam {len(results)} crop -> {OUT}")
    for r in results:
        print(f"  p{r['page']:3d} q{r['q']:02d} x={r['left']:6.1f}-{r['right']:6.1f} "
              f"y={r['top']:6.1f}-{r['bottom']:6.1f}")

if __name__ == "__main__":
    main()
