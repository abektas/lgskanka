#!/usr/bin/env python3
"""Detailed probe of tu2 layout: divider x, inline anchors, per-column question spans."""
from __future__ import annotations
import re
import statistics
from pathlib import Path
import pypdfium2 as pdfium

PDF = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/tip_1/tu2_turkce_2023.pdf")
ANCHOR_STANDALONE = re.compile(r"^(\d{1,3})\.$")
ANCHOR_INLINE = re.compile(r"^(\d{1,3})\.\s+\S")


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


def divider_candidates(page, W, H):
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
        if w > 20 or h < 0.2 * H:
            continue
        out.append({"x": round((x0 + x1) / 2, 1), "w": round(w, 1),
                    "h": round(h, 1), "y0": round(y0, 1), "y1": round(y1, 1)})
    return out


def main():
    doc = pdfium.PdfDocument(PDF)
    n = len(doc)

    # 1) Divider x distribution across all pages
    divs = []
    for p in range(n):
        page = doc[p]
        W, H = page.get_size()
        cands = divider_candidates(page, W, H)
        if cands:
            best = max(cands, key=lambda c: c["h"])
            if best["h"] > 0.3 * H:
                divs.append(best["x"])
    print("=== DIVIDER X DAĞILIMI ===")
    if divs:
        print(f"  ölçülen sayfa: {len(divs)}/{n}")
        print(f"  min={min(divs)} max={max(divs)} medyan={statistics.median(divs)}")
        from collections import Counter
        c = Counter(round(d) for d in divs)
        print(f"  en sık: {c.most_common(8)}")

    # 2) Anchor detection comparison on sample pages
    print("\n=== ANCHOR TESPİTİ (standalone vs inline) ===")
    sample = [8, 9, 10, 12, 22, 28, 36, 46, 61, 130, 152, 162, 178, 188]
    for p in sample:
        if p - 1 >= n:
            continue
        page = doc[p - 1]
        W, H = page.get_size()
        rects = page_rects(page)
        body = [r for r in rects if 90 < r["y0"] < H - 60]
        standalone = [r for r in body if ANCHOR_STANDALONE.fullmatch(r["text"])]
        inline = [r for r in body if ANCHOR_INLINE.match(r["text"])]
        print(f"  p{p:>4}: standalone={len(standalone):>2}  inline={len(inline):>2}  "
              f"inline_xs={[round(r['x0']) for r in inline]}")

    # 3) Detailed dump of one representative page
    print("\n=== ÖRNEK SAYFA DÖKÜMÜ (p9) ===")
    page = doc[8]
    W, H = page.get_size()
    rects = page_rects(page)
    for r in rects[:40]:
        tag = ""
        if ANCHOR_STANDALONE.fullmatch(r["text"]):
            tag = " <ANCHOR>"
        elif ANCHOR_INLINE.match(r["text"]):
            tag = " <ANCHOR-INLINE>"
        print(f"  x0={r['x0']:>6.1f} x1={r['x1']:>6.1f} y0={r['y0']:>6.1f} "
              f"{r['text'][:60]!r}{tag}")

    # 4) Divider candidates on p9
    print("\n=== p9 DİVİDER ADAYLARI ===")
    for c in divider_candidates(page, W, H):
        print(f"  x={c['x']:>6} w={c['w']:>5} h={c['h']:>6} y0={c['y0']:>6} y1={c['y1']:>6}")


if __name__ == "__main__":
    main()