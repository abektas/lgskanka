#!/usr/bin/env python3
"""Crop 2017 LGS practice exam PDFs into per-question PNGs."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pdfplumber

INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs_2017")
OUTPUT_DIR = Path("/home/selam/roller/web/lgs-ai-coach/lgs_18_26")
YEAR = 2017
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
    {"slug": "matematik", "name": "Matematik", "page_start": 3, "page_end": 8, "count": 20},
    {"slug": "fen-bilimleri", "name": "Fen Bilimleri", "page_start": 9, "page_end": 20, "count": 20},
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def parse_answer_key() -> dict[str, dict[int, str]]:
    """Parse answer key from the separate PDF using column positions."""
    import pdfplumber
    pdf_path = INPUT_DIR / "2017 Cevap Anahtarı.pdf"
    answers = {s: {} for s in ["turkce", "inkilap-tarihi", "din-kulturu", "ingilizce", "matematik", "fen-bilimleri"]}

    with pdfplumber.open(pdf_path) as pdf:
        # Page 1: Türkçe, İnkılap, Din, İngilizce
        page = pdf.pages[0]
        words = page.extract_words() or []
        lines = {}
        for w in words:
            top = round(float(w["top"]))
            lines.setdefault(top, []).append(w)

        for top, ws in lines.items():
            ws.sort(key=lambda w: float(w["x0"]))
            # Group into qnum-answer pairs by x position
            pairs = []
            i = 0
            while i < len(ws):
                w = ws[i]
                text = str(w["text"]).strip()
                m = re.match(r"^(\d{1,2})\.$", text)
                if m:
                    qnum = int(m.group(1))
                    # Find answer: next word with x0 close to qnum
                    for j in range(i + 1, min(i + 3, len(ws))):
                        next_text = str(ws[j]["text"]).strip()
                        if re.match(r"^[A-E]+$", next_text):
                            x0 = float(w["x0"])
                            if x0 < 130:
                                answers["turkce"][qnum] = next_text[0]
                            elif x0 < 260:
                                answers["inkilap-tarihi"][qnum] = next_text[0]
                            elif x0 < 380:
                                answers["din-kulturu"][qnum] = next_text[0]
                            else:
                                answers["ingilizce"][qnum] = next_text[0]
                            break
                i += 1

        # Page 2: Matematik, Fen
        if len(pdf.pages) > 1:
            page = pdf.pages[1]
            words = page.extract_words() or []
            lines = {}
            for w in words:
                top = round(float(w["top"]))
                lines.setdefault(top, []).append(w)

            for top, ws in lines.items():
                ws.sort(key=lambda w: float(w["x0"]))
                for i, w in enumerate(ws):
                    text = str(w["text"]).strip()
                    m = re.match(r"^(\d{1,2})\.$", text)
                    if m:
                        qnum = int(m.group(1))
                        for j in range(i + 1, min(i + 3, len(ws))):
                            next_text = str(ws[j]["text"]).strip()
                            if re.match(r"^[A-E]+$", next_text):
                                x0 = float(w["x0"])
                                if x0 < 260:
                                    answers["matematik"][qnum] = next_text[0]
                                else:
                                    answers["fen-bilimleri"][qnum] = next_text[0]
                                break

    for slug in answers:
        print(f"  {slug}: {len(answers[slug])} cevap bulundu")
    return answers

def extract_subject(pdf_path: Path, subject: dict, page_range: tuple, answer_key: dict[int, str], output_subdir: Path) -> list[dict]:
    """Extract questions for a single subject from a multi-subject PDF."""
    questions = []
    page_start, page_end = page_range

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        for page_idx in range(page_start - 1, page_end):
            if page_idx >= total_pages:
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
                    # Accept anchors in left column or center
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

                    # Use pdfplumber to get content bbox via text
                    # Simple approach: use anchor_top to next_limit
                    content_top = top
                    bottom = min(float(page.height), next_limit)
                    left = crop_left
                    right = crop_right

                    # Render with PIL (pymupdf)
                    import fitz
                    doc_fitz = fitz.open(str(pdf_path))
                    page_fitz = doc_fitz[page_idx]
                    mat = fitz.Matrix(DPI / 72, DPI / 72)
                    pix = page_fitz.get_pixmap(matrix=mat)
                    from PIL import Image
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

                    sx = img.width / float(page.width)
                    sy = img.height / float(page.height)

                    box = (round(left * sx), round(content_top * sy),
                           round(right * sx), round(bottom * sy))
                    if box[2] <= box[0] or box[3] <= box[1]:
                        print(f"    WARNING: Invalid crop box for Q{qnum}: {box}, skipping")
                        continue

                    out_path = output_subdir / f"MEB-LGS-2017-{subject['slug'].upper()}-Q{qnum:02d}.png"
                    cropped = img.crop(box)
                    if cropped.width == 0 or cropped.height == 0:
                        print(f"    WARNING: Empty crop for Q{qnum}: {box}, skipping")
                        continue
                    cropped.save(out_path, "PNG")

                    answer = answer_key.get(qnum)
                    if answer:
                        (output_subdir / f"MEB-LGS-2017-{subject['slug'].upper()}-Q{qnum:02d}.answer.txt").write_text(answer)

                    asset_hash = hashlib.sha256()
                    with out_path.open("rb") as f:
                        asset_hash.update(f.read())

                    questions.append({
                        "id": f"MEB-LGS-2017-{subject['slug'].upper()}-Q{qnum:02d}",
                        "questionNumber": qnum,
                        "page": page_num,
                        "column": column,
                        "representation": "IMAGE_BACKED",
                        "file": f"MEB-LGS-2017-{subject['slug'].upper()}-Q{qnum:02d}.png",
                        "visual": {
                            "publicPath": f"/exams/2017-{subject['slug']}-q{qnum:02d}.png",
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

    # Create output directories
    for subj in SOZEL_SUBJECTS + SAYISAL_SUBJECTS:
        (OUTPUT_DIR / subj["slug"]).mkdir(parents=True, exist_ok=True)

    all_questions_by_subject = {}

    # Process Sözel
    sozel_pdf = INPUT_DIR / "2017 Sözel.pdf"
    for subj in SOZEL_SUBJECTS:
        print(f"\n=== {subj['name']} (Sözel) ===")
        qs = extract_subject(sozel_pdf, subj, (subj["page_start"], subj["page_end"]),
                             all_answers.get(subj["slug"], {}), OUTPUT_DIR / subj["slug"])
        all_questions_by_subject[subj["slug"]] = qs
        print(f"  Extracted: {len(qs)} soru")

    # Process Sayısal
    sayisal_pdf = INPUT_DIR / "2017 Sayısal.pdf"
    for subj in SAYISAL_SUBJECTS:
        print(f"\n=== {subj['name']} (Sayısal) ===")
        qs = extract_subject(sayisal_pdf, subj, (subj["page_start"], subj["page_end"]),
                             all_answers.get(subj["slug"], {}), OUTPUT_DIR / subj["slug"])
        all_questions_by_subject[subj["slug"]] = qs
        print(f"  Extracted: {len(qs)} soru")

    # Create manifests per subject
    for slug, qs in all_questions_by_subject.items():
        manifest = {
            "manifestVersion": "1.0",
            "status": "NEEDS_REVIEW",
            "published": True,
            "source": {
                "sourceId": "2017-DENEME",
                "sourceType": "MEB_EXAM",
                "subject": slug,
                "period": "2016-2017"
            },
            "questions": qs,
            "answerKeyCandidates": {str(q["questionNumber"]): q["answer"] for q in qs if q["answer"]},
            "summary": {
                "questionsExtracted": len(qs),
                "expectedQuestions": len(qs)
            }
        }
        manifest_path = OUTPUT_DIR / slug / f"manifest_2017.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        print(f"\nManifest yazıldı: {manifest_path} ({len(qs)} soru)")

    print("\nTamamlandı!")


if __name__ == "__main__":
    main()
