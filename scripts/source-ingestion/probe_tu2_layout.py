#!/usr/bin/env python3
"""Probe tu2_turkce_2023.pdf layout: column structure, anchors, divider."""
from __future__ import annotations
import re
import sys
from pathlib import Path
import pypdfium2 as pdfium

PDF = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/tip_1/tu2_turkce_2023.pdf")
ANCHOR = re.compile(r"^(\d{1,3})\.$")


def page_rects(page):
    tp = page.get_textpage()
    H = page.get_size()[1]
    out = []
    for i in range(tp.count_rects()):
        l, b, r, t = tp.get_rect(i)
        txt = tp.get_text_bounded(l, b, r, t)
        if txt and txt.strip():
            out.append({"x0": float(l), "x1": float(r),
                        "y0": H - float(t), "y1": H - float(b),
                        "text": txt.strip()})
    out.sort(key=lambda r: (r["y0"], r["x0"]))
    return out


def text_x_gap(rects, W, H):
    """Find the widest empty vertical band in the middle third of the page."""
    # Only consider body text (exclude header/footer)
    body = [r for r in rects if 90 < r["y0"] < H - 60]
    if not body:
        return None
    # Histogram of x coverage (1pt bins)
    bins = [0] * int(W + 1)
    for r in body:
        a, b = max(0, int(r["x0"])), min(int(W), int(r["x1"]))
        for x in range(a, b + 1):
            bins[x] = 1
    # Search for widest run of zeros within middle third
    lo, hi = int(W * 0.33), int(W * 0.67)
    best_len, best_x, cur_len, cur_start = 0, None, 0, None
    for x in range(lo, hi):
        if bins[x] == 0:
            if cur_len == 0:
                cur_start = x
            cur_len += 1
            if cur_len > best_len:
                best_len, best_x = cur_len, cur_start + cur_len // 2
        else:
            cur_len = 0
    if best_len < 8:
        return None
    return {"x": best_x, "width": best_len}


def vertical_shapes(page, W, H):
    """Find tall narrow shapes (possible printed dividers)."""
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
        if w > 20:
            continue
        if h < 0.25 * H:
            continue
        out.append({"x": (x0 + x1) / 2, "w": w, "h": h, "y0": y0, "y1": y1})
    return out


def main():
    doc = pdfium.PdfDocument(PDF)
    n = len(doc)
    print(f"PDF: {n} pages\n")

    print(f"{'pg':>4} {'W':>6} {'H':>6} {'rects':>6} {'anch':>5} {'col1_x':>7} {'col2_x':>7} {'gap':>10} {'divider':>10}  verdict")
    two_col = 0
    one_col = 0
    per_page = {}

    for p in range(0, n):
        page = doc[p]
        W, H = page.get_size()
        rects = page_rects(page)
        anchors = [r for r in rects if ANCHOR.fullmatch(r["text"])
                   and 90 < r["y0"] < H - 60]
        # left-ish and right-ish anchors
        left = [a["x0"] for a in anchors if a["x0"] < W * 0.45]
        right = [a["x0"] for a in anchors if a["x0"] >= W * 0.45]
        gap = text_x_gap(rects, W, H)
        vs = vertical_shapes(page, W, H)
        div_x = None
        if vs:
            # longest vertical shape
            best = max(vs, key=lambda s: s["h"])
            div_x = best["x"]

        verdict = "-"
        if anchors:
            if len(right) >= 2 and len(left) >= 1:
                verdict = "TWO-COL"
                two_col += 1
            elif len(right) >= 1 and len(left) == 0:
                verdict = "right-only"
            else:
                verdict = "ONE-COL"
                one_col += 1

        per_page[p + 1] = {"verdict": verdict, "left": left, "right": right,
                           "gap": gap, "divider": div_x, "n_anchors": len(anchors)}

        if anchors or vs:
            print(f"{p+1:>4} {W:>6.0f} {H:>6.0f} {len(rects):>6} {len(anchors):>5} "
                  f"{(min(left) if left else -1):>7.0f} {(min(right) if right else -1):>7.0f} "
                  f"{(gap['x'] if gap else -1):>10} {(div_x if div_x else -1):>10.0f}  {verdict}")

    print(f"\nÖzet: TWO-COL={two_col}  ONE-COL={one_col}")
    # compact listing of 2-col pages
    tc = [p for p, v in per_page.items() if v["verdict"] == "TWO-COL"]
    if tc:
        print(f"TWO-COL sayfalar: {tc[:60]}{' ...' if len(tc) > 60 else ''}")


if __name__ == "__main__":
    main()