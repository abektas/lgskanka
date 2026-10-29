#!/usr/bin/env python3
"""Classify tu2 anchors: real question anchors (column margin) vs in-question list items."""
from __future__ import annotations
import re
from pathlib import Path
from collections import Counter
import pypdfium2 as pdfium

PDF = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/tip_1/tu2_turkce_2023.pdf")
STANDALONE = re.compile(r"^(\d{1,3})\.$")
DIVIDER_X = 297.6
LEFT_MARGIN = (24, 34)      # real left-column anchors
RIGHT_MARGIN = (305, 314)   # real right-column anchors


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


def classify(rects, H):
    left_real, right_real, other = [], [], []
    for r in rects:
        m = STANDALONE.fullmatch(r["text"])
        if not m:
            continue
        if not (90 < r["y0"] < H - 60):
            continue
        n = int(m.group(1))
        if LEFT_MARGIN[0] <= r["x0"] <= LEFT_MARGIN[1]:
            left_real.append((n, r["y0"]))
        elif RIGHT_MARGIN[0] <= r["x0"] <= RIGHT_MARGIN[1]:
            right_real.append((n, r["y0"]))
        else:
            other.append((n, round(r["x0"], 1), round(r["y0"], 1)))
    return left_real, right_real, other


def main():
    doc = pdfium.PdfDocument(PDF)
    n = len(doc)

    print(f"{'pg':>4} | {'LEFT real':<22} | {'RIGHT real':<22} | other_count")
    total_left = total_right = total_other = 0
    seq_issues = []

    for p in range(7, 192):  # question pages
        page = doc[p]
        W, H = page.get_size()
        rects = page_rects(page)
        left, right, other = classify(rects, H)
        total_left += len(left)
        total_right += len(right)
        total_other += len(other)
        ltxt = ",".join(str(x[0]) for x in left) or "-"
        rtxt = ",".join(str(x[0]) for x in right) or "-"
        if left or right or other:
            print(f"{p+1:>4} | {ltxt:<22} | {rtxt:<22} | {len(other)}")

    print(f"\nToplam: LEFT real={total_left}  RIGHT real={total_right}  other={total_other}")
    print(f"Gerçek anchor toplamı: {total_left + total_right}")

    # Check 'other' x distribution — should be indented list items
    allother = []
    for p in range(7, 192):
        page = doc[p]
        W, H = page.get_size()
        rects = page_rects(page)
        _, _, other = classify(rects, H)
        allother.extend(x[1] for x in other)
    if allother:
        c = Counter(round(x) for x in allother)
        print(f"\n'other' x dağılımı (ilk 10): {c.most_common(10)}")


if __name__ == "__main__":
    main()