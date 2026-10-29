#!/usr/bin/env python3
"""Crop 2015 LGS practice exam PDFs into per-question PNGs."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pdfplumber
import fitz
from PIL import Image

INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs 2015")
OUTPUT_DIR = Path("/home/selam/roller/web/lgs-ai-coach/lgs_18_26")
YEAR = 2015
DPI = 300
MARGIN_PT = 20.0
FOOTER_PT = 70.0
QUESTION_RE = re.compile(r"^(\d{1,2})\.$")

# Subject page ranges (1-indexed) in each PDF
SOZEL_SUBJECTS = [
    {"slug": "turkce", "name": "Türkçe", "page_start": 3, "page_end": 10, "count": 20},
    {"slug": "inkilap-tarihi", "name": "T.C. İnkılap Tarihi ve Atatürkçülük", "page_start": 11, "page_end": 14, "count": 10},
    {"slug": "din-kulturu", "name": "Din Kültürü ve Ahlak Bilgisi", "page_start": 15, "page_end": 17, "count": 10},
    {"slug": "ingilizce", "name": "Yabancı Dil (İngilizce)", "page_start": 18, "page_end": 22, "count": 10},
]
SAYISAL_SUBJECTS = [
    {"slug": "matematik", "name": "Matematik", "page_start": 3, "page_end": 11, "count": 20},
    {"slug": "fen-bilimleri", "name": "Fen Bilimleri", "page_start": 12, "page_end": 21, "count": 20},
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def parse_answer_key() -> dict[str, dict[int, str]]:
    """Parse answer key from the separate PDF (4-column grid on page 1, 2-column on page 2)."""
    pdf_path = INPUT_DIR / "2015 Cevap Anahtarı.pdf"
    answers = {s: {} for s in ["turkce", "inkilap-tarihi", "din-kulturu", "ingilizce", "matematik", "fen-bilimleri"]}
    
    with pdfplumber.open(pdf_path) as pdf:
        # Page 1: 4 columns (turkce, inkilap, din, ingilizce)
        page = pdf.pages[0]
        words = page.extract_words() or []
        
        # Group by top position (rows)
        rows = {}
        for w in words:
            top = round(float(w["top"]))
            rows.setdefault(top, []).append(w)
        
        # Column x positions from data:
        # turkce: qnum~65, ans~93
        # inkilap: qnum~183, ans~215
        # din: qnum~305, ans~337
        # ingilizce: qnum~427, ans~459
        col_configs = [
            ("turkce", 40, 130),
            ("inkilap-tarihi", 150, 250),
            ("din-kulturu", 270, 370),
            ("ingilizce", 400, 500),
        ]
        
        for top, ws in sorted(rows.items()):
            ws.sort(key=lambda w: float(w["x0"]))
            for subject, x_min, x_max in col_configs:
                col_words = [w for w in ws if x_min <= float(w["x0"]) <= x_max]
                col_words.sort(key=lambda w: float(w["x0"]))
                
                for i, w in enumerate(col_words):
                    text = str(w.get("text", "")).strip()
                    match = re.match(r"^(\d{1,2})\.$", text)
                    if match:
                        qnum = int(match.group(1))
                        for j in range(i + 1, min(i + 3, len(col_words))):
                            next_text = str(col_words[j].get("text", "")).strip()
                            if re.match(r"^[A-E]$", next_text):
                                answers[subject][qnum] = next_text[0]
                                break
        
        # Page 2: 2 columns (matematik, fen-bilimleri)
        if len(pdf.pages) > 1:
            page = pdf.pages[1]
            words = page.extract_words() or []
            
            rows = {}
            for w in words:
                top = round(float(w["top"]))
                rows.setdefault(top, []).append(w)
            
            # Page 2: matematik (left col ~184), fen (right col ~377)
            col_configs = [
                ("matematik", 150, 280),
                ("fen-bilimleri", 320, 450),
            ]
            
            for top, ws in sorted(rows.items()):
                ws.sort(key=lambda w: float(w["x0"]))
                for subject, x_min, x_max in col_configs:
                    col_words = [w for w in ws if x_min <= float(w["x0"]) <= x_max]
                    col_words.sort(key=lambda w: float(w["x0"]))
                    
                    for i, w in enumerate(col_words):
                        text = str(w.get("text", "")).strip()
                        match = re.match(r"^(\d{1,2})\.$", text)
                        if match:
                            qnum = int(match.group(1))
                            for j in range(i + 1, min(i + 3, len(col_words))):
                                next_text = str(col_words[j].get("text", "")).strip()
                                if re.match(r"^[A-E]$", next_text):
                                    answers[subject][qnum] = next_text[0]
                                    break
    
    for slug in answers:
        print(f"  {slug}: {len(answers[slug])} cevap bulundu")
    return answers


def extract_subject(pdf_path: Path, subject: dict, page_range: tuple, answer_key: dict[int, str], output_subdir: Path) -> list[dict]:
    questions = []
    page_start, page_end = page_range

    # Pre-extract D option positions for all pages in range
    d_options_by_page = {}
    with pdfplumber.open(pdf_path) as pdf_check:
        for page_idx in range(page_start - 1, min(page_end, len(pdf_check.pages))):
            page = pdf_check.pages[page_idx]
            words = page.extract_words() or []
            d_tops = []
            for w in words:
                text = str(w.get("text", "")).strip()
                if text == "D)":
                    d_tops.append(float(w["top"]))
            if d_tops:
                d_options_by_page[page_idx + 1] = max(d_tops) + MARGIN_PT  # max D top + 20pt

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx in range(page_start - 1, page_end):
            if page_idx >= len(pdf.pages):
                break
            page = pdf.pages[page_idx]
            page_num = page_idx + 1
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []

            anchors = []
            for w in words:
                text = str(w.get("text", "")).strip()
                match = QUESTION_RE.fullmatch(text)
                if match:
                    qnum = int(match.group(1))
                    x0 = float(w["x0"])
                    top = float(w["top"])
                    if x0 <= 80 or page.width / 2 - 5 <= x0 <= page.width / 2 + 55:
                        anchors.append((qnum, x0, top))

            if not anchors:
                continue

            left_anchors = [a for a in anchors if a[1] < page.width / 2]
            right_anchors = [a for a in anchors if a[1] >= page.width / 2]

            if left_anchors and right_anchors:
                column_groups = {"left": left_anchors, "right": right_anchors}
                bounds = {
                    "left": (MARGIN_PT, page.width / 2 - 5, 0.0, page.width / 2 - 5),
                    "right": (page.width / 2 + 5, page.width - MARGIN_PT, page.width / 2 + 5, page.width),
                }
            else:
                column_groups = {"single": anchors}
                bounds = {"single": (MARGIN_PT, page.width - MARGIN_PT, 0.0, page.width)}

            # Render page with pymupdf
            doc_fitz = fitz.open(str(pdf_path))
            page_fitz = doc_fitz[page_idx]
            mat = fitz.Matrix(DPI / 72, DPI / 72)
            pix = page_fitz.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

            sx = img.width / float(page.width)
            sy = img.height / float(page.height)

            for column, col_anchors in column_groups.items():
                col_anchors.sort(key=lambda a: a[2])
                crop_left, crop_right, scan_left, scan_right = bounds.get(column, bounds.get("single", (MARGIN_PT, page.width - MARGIN_PT, 0.0, page.width)))

                for idx, (qnum, _x0, anchor_top) in enumerate(col_anchors):
                    if qnum in [q["questionNumber"] for q in questions]:
                        continue

                    top = max(0.0, anchor_top - MARGIN_PT)
                    if idx + 1 < len(col_anchors):
                        next_limit = col_anchors[idx + 1][2] - MARGIN_PT
                    else:
                        next_limit = page.height - FOOTER_PT

                    content_top = top
                    # For last question on page, use pre-extracted D option position
                    if idx + 1 >= len(col_anchors) and page_num in d_options_by_page:
                        bottom = max(min(float(page.height), next_limit), d_options_by_page[page_num])
                    else:
                        bottom = min(float(page.height), next_limit)
                    
                    content_top = top
                    left = crop_left
                    right = crop_right
                    
                    # For last question on page, check if D option extends beyond next_limit
                    if idx + 1 >= len(col_anchors):
                        # Look for D option in right column area
                        with pdfplumber.open(pdf_path) as pdf_check:
                            page_check = pdf_check.pages[page_idx]
                            words_check = page_check.extract_words() or []
                            for w in words_check:
                                text = str(w.get("text", "")).strip()
                                if text == "D)" and float(w["top"]) > next_limit - 50:
                                    bottom = max(bottom, float(w["top"]) + MARGIN_PT)
                                    break

                    box = (round(left * sx), round(content_top * sy),
                           round(right * sx), round(bottom * sy))
                    if box[2] <= box[0] or box[3] <= box[1]:
                        print(f"    WARNING: Invalid crop box for Q{qnum}: {box}, skipping")
                        continue

                    out_path = output_subdir / f"MEB-LGS-2015-{subject['slug'].upper()}-Q{qnum:02d}.png"
                    cropped = img.crop(box)
                    if cropped.width == 0 or cropped.height == 0:
                        print(f"    WARNING: Empty crop for Q{qnum}: {box}, skipping")
                        continue
                    cropped.save(out_path, "PNG")

                    answer = answer_key.get(qnum)
                    if answer:
                        (output_subdir / f"MEB-LGS-2015-{subject['slug'].upper()}-Q{qnum:02d}.answer.txt").write_text(answer)

                    asset_hash = hashlib.sha256()
                    with out_path.open("rb") as f:
                        asset_hash.update(f.read())

                    questions.append({
                        "id": f"MEB-LGS-2015-{subject['slug'].upper()}-Q{qnum:02d}",
                        "questionNumber": qnum,
                        "page": page_num,
                        "column": column,
                        "representation": "IMAGE_BACKED",
                        "file": f"MEB-LGS-2015-{subject['slug'].upper()}-Q{qnum:02d}.png",
                        "visual": {
                            "publicPath": f"/exams/2015-{subject['slug']}-q{qnum:02d}.png",
                            "clipRectPt": {"x0": round(left, 3), "y0": round(content_top, 3),
                                          "x1": round(right, 3), "y1": round(bottom, 3)},
                            "renderDpi": DPI,
                            "authority": "ORIGINAL_MEB_PDF",
                            "reconstructedFromOcr": False,
                            "assetSha256": asset_hash.hexdigest()
                        },
                        "answer": answer,
                        "status": "NEEDS_REVIEW",
                        "published": True,
                        "subject": subject["slug"]
                    })
                    print(f"    Q{qnum}: answer={answer}")

    return questions


def main():
    all_answers = parse_answer_key()

    for subj in SOZEL_SUBJECTS + SAYISAL_SUBJECTS:
        (OUTPUT_DIR / subj["slug"]).mkdir(parents=True, exist_ok=True)

    all_questions_by_subject = {}

    sozel_pdf = INPUT_DIR / "2015 Sözel.pdf"
    for subj in SOZEL_SUBJECTS:
        print(f"\n=== {subj['name']} (Sözel) ===")
        qs = extract_subject(sozel_pdf, subj, (subj["page_start"], subj["page_end"]),
                             all_answers.get(subj["slug"], {}), OUTPUT_DIR / subj["slug"])
        all_questions_by_subject[subj["slug"]] = qs
        print(f"  Extracted: {len(qs)} soru")

    sayisal_pdf = INPUT_DIR / "2015 Sayısal.pdf"
    for subj in SAYISAL_SUBJECTS:
        print(f"\n=== {subj['name']} (Sayısal) ===")
        qs = extract_subject(sayisal_pdf, subj, (subj["page_start"], subj["page_end"]),
                             all_answers.get(subj["slug"], {}), OUTPUT_DIR / subj["slug"])
        all_questions_by_subject[subj["slug"]] = qs
        print(f"  Extracted: {len(qs)} soru")

    for slug, qs in all_questions_by_subject.items():
        manifest = {
            "manifestVersion": "1.0",
            "status": "NEEDS_REVIEW",
            "published": True,
            "source": {
                "sourceId": "2015-DENEME",
                "sourceType": "MEB_EXAM",
                "subject": slug,
                "period": "2014-2015"
            },
            "questions": qs,
            "answerKeyCandidates": {str(q["questionNumber"]): q["answer"] for q in qs if q["answer"]},
            "summary": {
                "questionsExtracted": len(qs),
                "expectedQuestions": len(qs)
            }
        }
        manifest_path = OUTPUT_DIR / slug / f"manifest_2015.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nManifest yazıldı: {manifest_path} ({len(qs)} soru)")

    print("\nTamamlandı!")


if __name__ == "__main__":
    main()