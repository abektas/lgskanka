#!/usr/bin/env python3
"""Fast bounded layout probe for tip_1 workbooks: samples first/last pages only."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pdfplumber

BASE = Path("/media/selam/Yeni Birim/Lgs Temel Kaynaklar/lgs_çalışma_soruları/tip_1")
QRE = re.compile(r"^(\d{1,2})[.)]?$")
HEADERS = ["FEN BİLİMLERİ", "MATEMATİK", "TÜRKÇE", "T.C. İNKILAP", "İNKILAP",
           "DİN KÜLTÜRÜ", "İNGİLİZCE", "YABANCI DİL", "CEVAP ANAHTARI", "CEVAPLAR"]


def probe(path: Path, head: int = 14, tail: int = 14):
    print(f"\n{'='*78}\n{path.name}\n{'='*78}")
    with pdfplumber.open(path) as pdf:
        n = len(pdf.pages)
        p0 = pdf.pages[0]
        print(f"pages={n} size={p0.width:.1f}x{p0.height:.1f}")
        idxs = list(range(1, min(head, n) + 1)) + list(range(max(1, n - tail + 1), n + 1))
        for i in sorted(set(idxs)):
            page = pdf.pages[i - 1]
            text = page.extract_text() or ""
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
            anchors = []
            for w in words:
                m = QRE.fullmatch(str(w.get("text", "")).strip())
                if m and 1 <= int(m.group(1)) <= 90:
                    anchors.append((int(m.group(1)), round(float(w["x0"]), 1), round(float(w["top"]), 1)))
            vsegs = []
            for ln in page.lines or []:
                x0, x1 = float(ln["x0"]), float(ln["x1"])
                t, b = float(ln["top"]), float(ln["bottom"])
                if abs(x0 - x1) < 5 and (b - t) > page.height * 0.10:
                    vsegs.append((round((x0 + x1) / 2, 1), round(b - t, 1)))
            hdr = [h for h in HEADERS if h in text.upper()]
            first_line = (text.splitlines() or [""])[0][:70]
            print(f" p{i:>3}: anchors={len(anchors)} x0s={sorted({a[1] for a in anchors})[:6]} "
                  f"segs={vsegs[:3]} hdr={hdr[:2]} | {first_line}")


def main():
    for f in sorted(BASE.glob("*.pdf")):
        probe(f)


if __name__ == "__main__":
    sys.exit(main())
