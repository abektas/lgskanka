#!/usr/bin/env python3
"""Layout inspection for tip_1 study-workbook PDFs before v21 batch extraction.

Reports, per PDF: page count/size, pages containing question-number anchors,
anchor x-positions (column evidence), vertical divider segments from page.lines,
and answer-key page candidates.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pdfplumber

BASE = Path("/media/selam/Yeni Birim/Lgs Temel Kaynaklar/lgs_çalışma_soruları/tip_1")
QUESTION_RE = re.compile(r"^(\d{1,2})[.)]?$")


def vertical_segments(page):
    segs = []
    for line in page.lines or []:
        x0, x1 = float(line["x0"]), float(line["x1"])
        top, bottom = float(line["top"]), float(line["bottom"])
        if abs(x0 - x1) < 5 and (bottom - top) > page.height * 0.10:
            segs.append((round((x0 + x1) / 2, 1), round(bottom - top, 1)))
    return segs


def inspect(path: Path, max_report_pages: int = 6):
    print(f"\n{'='*80}\n{path.name}\n{'='*80}")
    with pdfplumber.open(path) as pdf:
        n = len(pdf.pages)
        p0 = pdf.pages[0]
        print(f"pages={n}  size={p0.width:.1f}x{p0.height:.1f}")

        pages_with_anchors = []
        answer_pages = []
        subject_header_pages = []
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            upper = text.upper()
            if "CEVAP" in upper and ("ANAHTAR" in upper or "CEVAPLAR" in upper):
                answer_pages.append(i)
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
            anchors = []
            for w in words:
                m = QUESTION_RE.fullmatch(str(w.get("text", "")).strip())
                if m and 1 <= int(m.group(1)) <= 90:
                    anchors.append((int(m.group(1)), round(float(w["x0"]), 1), round(float(w["top"]), 1)))
            if anchors:
                pages_with_anchors.append((i, anchors, vertical_segments(page)))
            # subject header keywords
            for kw in ["FEN BİLİMLERİ", "MATEMATİK", "TÜRKÇE", "T.C. İNKILAP", "İNKILAP TARİHİ",
                       "DİN KÜLTÜRÜ", "İNGİLİZCE", "YABANCI DİL"]:
                if kw in upper:
                    subject_header_pages.append((i, kw))
                    break

        print(f"pages_with_anchors={len(pages_with_anchors)}")
        print(f"answer_key_pages={answer_pages[:20]}{' ...' if len(answer_pages) > 20 else ''} (total {len(answer_pages)})")
        print(f"subject_header_pages(first 15)={subject_header_pages[:15]}")

        for i, anchors, segs in pages_with_anchors[:max_report_pages]:
            xs = sorted({a[1] for a in anchors})
            print(f"  p{i}: n_anchors={len(anchors)} x0s={xs[:10]} segs={segs[:4]}")

        # last content pages
        if pages_with_anchors:
            print("  first anchor page:", pages_with_anchors[0][0],
                  "last anchor page:", pages_with_anchors[-1][0])

        # sample first real content page text
        if pages_with_anchors:
            fp = pages_with_anchors[0][0]
            print(f"  --- p{fp} text (first 12 lines) ---")
            for line in (pdf.pages[fp - 1].extract_text() or "").splitlines()[:12]:
                print("    |", line[:110])
        if answer_pages:
            ap = answer_pages[0]
            print(f"  --- p{ap} ANSWER text (first 14 lines) ---")
            for line in (pdf.pages[ap - 1].extract_text() or "").splitlines()[:14]:
                print("    |", line[:110])


def main():
    files = sorted(p for p in BASE.glob("*.pdf"))
    for f in files:
        inspect(f)


if __name__ == "__main__":
    sys.exit(main())
