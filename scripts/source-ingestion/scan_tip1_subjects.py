#!/usr/bin/env python3
"""Scan every page of tip_1 workbooks for subject headers and answer-key pages."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pdfplumber

BASE = Path("/media/selam/Yeni Birim/Lgs Temel Kaynaklar/lgs_çalışma_soruları/tip_1")
OUT = Path("/home/selam/roller/web/lgs-ai-coach/logs/tip1_page_scan.json")

HEADER_PATTERNS = {
    "fen-bilimleri": ["FEN BİLİMLERİ"],
    "matematik": ["MATEMATİK"],
    "turkce": ["TÜRKÇE"],
    "inkilap-tarihi": ["T.C. İNKILAP", "İNKILAP TARİHİ", "ATATÜRKÇÜLÜK"],
    "din-kulturu": ["DİN KÜLTÜRÜ", "AHLAK BİLGİSİ"],
    "ingilizce": ["İNGİLİZCE", "YABANCI DİL", "ENGLISH"],
}
ANSWER_MARKERS = ["CEVAP ANAHTARI", "CEVAPLAR", "ANSWER KEY"]


def main():
    report = {}
    for pdf_path in sorted(BASE.glob("*.pdf")):
        with pdfplumber.open(pdf_path) as pdf:
            n = len(pdf.pages)
            headers = {k: [] for k in HEADER_PATTERNS}
            answers = []
            empty_text = []
            for i, page in enumerate(pdf.pages, 1):
                text = (page.extract_text() or "").upper()
                if not text.strip():
                    empty_text.append(i)
                for slug, pats in HEADER_PATTERNS.items():
                    if any(p in text for p in pats):
                        headers[slug].append(i)
                if any(m in text for m in ANSWER_MARKERS):
                    answers.append(i)
        report[pdf_path.name] = {
            "pages": n,
            "headers": {k: v for k, v in headers.items() if v},
            "answer_pages": answers,
            "empty_text_pages": empty_text,
        }
        print(f"\n=== {pdf_path.name} ({n} pages) ===")
        for slug, pages in report[pdf_path.name]["headers"].items():
            print(f"  {slug:16s}: {pages[:40]}{' ...' if len(pages) > 40 else ''} (n={len(pages)})")
        print(f"  answer_pages    : {answers}")
        print(f"  empty_text_pages: {empty_text[:30]}{' ...' if len(empty_text) > 30 else ''} (n={len(empty_text)})")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[saved] {OUT}")


if __name__ == "__main__":
    sys.exit(main())
