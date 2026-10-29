#!/usr/bin/env python3
"""2015 LGS proper extractor - anchor-based cropping with proper column splitting and D-option table extent detection."""
import json
import hashlib
import re
from pathlib import Path
import fitz
from PIL import Image
import pdfplumber

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs 2015")
OUTPUT_DIR = REPO / "lgs_18_26"
DPI = 300
MARGIN_PT = 20.0
FOOTER_PT = 70.0
QUESTION_RE = re.compile(r"^(\d{1,2})\.$")

# Subject page ranges (verified from PDF text analysis)
SOZEL_SUBJECTS = [
    {"slug": "turkce", "name": "Türkçe", "page_start": 3, "page_end": 10, "pdf": "2015 Sözel.pdf", "count": 20},
    {"slug": "inkilap-tarihi", "name": "T.C. İnkılap Tarihi ve Atatürkçülük", "page_start": 11, "page_end": 14, "pdf": "2015 Sözel.pdf", "count": 10},
    {"slug": "din-kulturu", "name": "Din Kültürü ve Ahlak Bilgisi", "page_start": 15, "page_end": 17, "pdf": "2015 Sözel.pdf", "count": 10},
    {"slug": "ingilizce", "name": "Yabancı Dil (İngilizce)", "page_start": 18, "page_end": 22, "pdf": "2015 Sözel.pdf", "count": 10},
]
SAYISAL_SUBJECTS = [
    {"slug": "matematik", "name": "Matematik", "page_start": 3, "page_end": 11, "pdf": "2015 Sayısal.pdf", "count": 20},
    {"slug": "fen-bilimleri", "name": "Fen Bilimleri", "page_start": 12, "page_end": 21, "pdf": "2015 Sayısal.pdf", "count": 20},
]

DPI = 300
MARGIN_PT = 20.0
FOOTER_PT = 70.0
QUESTION_RE = re.compile(r"^(\d{1,2})\.$")

PAGE_WIDTH_PT = 552.756
PAGE_HEIGHT_PT = 779.528
COL_CENTER_PT = PAGE_WIDTH_PT / 2

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def find_anchors_on_page(page, page_width):
    """Find all question number anchors on a page."""
    anchors = []
    for w in page.extract_words(use_text_flow=False, keep_blank_chars=False) or []:
        text = str(w.get("text", "")).strip()
        match = QUESTION_RE.fullmatch(text)
        if match:
            qnum = int(match.group(1))
            x0 = float(w["x0"])
            top = float(w["top"])
            if x0 <= 80 or abs(x0 - COL_CENTER_PT) <= 10:
                column = "left" if x0 < COL_CENTER_PT else "right"
                anchors.append({"qnum": qnum, "x0": x0, "top": top, "column": column})
    return anchors


def find_d_option_table_bottom(page, column=None):
    """Find the bottom of the D-option table (not just D marker), per column."""
    words = page.extract_words() or []
    
    # Find D) marker positions
    d_markers = []
    for w in words:
        text = str(w.get("text", "")).strip()
        if text == "D)":
            x0 = float(w["x0"])
            top = float(w["top"])
            # Filter by column
            if column == "left" and x0 < COL_CENTER_PT:
                d_markers.append(top)
            elif column == "right" and x0 >= COL_CENTER_PT:
                d_markers.append(top)
            elif column is None:
                d_markers.append(top)
    
    if not d_markers:
        return None
    
    d_top = max(d_markers)  # lowest D marker in this column
    
    # Find table content below D) - look for table keywords
    table_keywords = {"Sporcu", "Galibiyet", "Mert", "Aydan", "Cansu", "Kerim", "Anne", "Baba", "Mert", "1", "2", "3", "4"}
    table_bottom = max(d_markers)  # at minimum, D marker position
    
    for w in page.extract_words() or []:
        text = str(w.get("text", "")).strip()
        w_top = float(w["top"])
        w_x0 = float(w["x0"])
        # Filter by column
        if column == "left" and w_x0 >= COL_CENTER_PT:
            continue
        if column == "right" and w_x0 < COL_CENTER_PT:
            continue
        # Look for table content below D marker
        if w_top > max(d_markers) and text in {"Sporcu", "Galibiyet", "Mert", "Aydan", "Cansu", "Kerim", "Anne", "Baba", "Sporcu", "Galibiyet"}:
            table_bottom = max(table_bottom, w_top + 15)
        # Also detect numeric table cells
        if w_top > max(d_markers) and text.isdigit() and 1 <= int(text) <= 4:
            table_bottom = max(table_bottom, w_top + 10)
    
    # Add margin
    return min(table_bottom + MARGIN_PT, 779.528 - 70)


def parse_answer_key() -> dict[str, dict[int, str]]:
    pdf_path = INPUT_DIR / "2015 Cevap Anahtarı.pdf"
    answers = {s: {} for s in ["turkce", "inkilap-tarihi", "din-kulturu", "ingilizce", "matematik", "fen-bilimleri"]}
    
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words() or []
        rows = {}
        for w in words:
            top = round(float(w["top"]))
            rows.setdefault(top, []).append(w)
        
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
        
        if len(pdf.pages) > 1:
            page = pdf.pages[1]
            words = page.extract_words() or []
            rows = {}
            for w in words:
                top = round(float(w["top"]))
                rows.setdefault(top, []).append(w)
            
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
        print(f"  {slug}: {len(answers[slug])} cevap")
    return answers


def extract_subject(pdf_path: Path, subject: dict, page_range: tuple, answer_key: dict[int, str], output_subdir: Path) -> list[dict]:
    """Extract questions for a subject using anchor-based cropping."""
    questions = []
    page_start, page_end = page_range
    extracted_qnums = set()  # Track globally extracted question numbers for this subject

    with pdfplumber.open(pdf_path) as pdf:
        doc_fitz = fitz.open(str(pdf_path))
        
        for page_idx in range(page_start - 1, page_end):
            if page_idx >= len(pdf.pages):
                break
            page = pdf.pages[page_idx]
            page_num = page_idx + 1
            
            # Find anchors on this page
            anchors = []
            seen_anchors = set()  # Track (qnum, column, page_idx) to deduplicate
            for w in page.extract_words(use_text_flow=False, keep_blank_chars=False) or []:
                text = str(w.get("text", "")).strip()
                match = QUESTION_RE.fullmatch(text)
                if match:
                    qnum = int(match.group(1))
                    x0 = float(w["x0"])
                    top = float(w["top"])
                    if x0 <= 80 or abs(x0 - COL_CENTER_PT) <= 10:
                        column = "left" if x0 < COL_CENTER_PT else "right"
                        # Deduplicate: keep only first occurrence per (qnum, column, page_idx)
                        key = (qnum, column, page_idx)
                        if key not in seen_anchors and top >= 75:  # Filter out header "7. Deneme"
                            seen_anchors.add(key)
                            anchors.append({"qnum": qnum, "x0": x0, "top": top, "column": column})
            
            if not anchors:
                continue

            # Filter out already extracted question numbers
            anchors = [a for a in anchors if a["qnum"] not in extracted_qnums]
            if not anchors:
                continue
            
            # Separate by column
            left_anchors = [a for a in anchors if a["column"] == "left"]
            right_anchors = [a for a in anchors if a["column"] == "right"]
            left_anchors.sort(key=lambda a: a["top"])
            right_anchors.sort(key=lambda a: a["top"])
            
            # Determine column bounds
            if left_anchors and right_anchors:
                column_groups = {"left": left_anchors, "right": right_anchors}
                bounds = {
                    "left": (MARGIN_PT, COL_CENTER_PT - 5, 0.0, COL_CENTER_PT - 5),
                    "right": (COL_CENTER_PT + 5, PAGE_WIDTH_PT - MARGIN_PT, COL_CENTER_PT + 5, PAGE_WIDTH_PT),
                }
            else:
                column_groups = {"single": anchors}
                bounds = {"single": (MARGIN_PT, PAGE_WIDTH_PT - MARGIN_PT, 0.0, PAGE_WIDTH_PT)}

            # Find D-option table bottom for this page (per column)
            # We'll compute per-column D bottom inside the loop
            d_bottom_per_column = {}
            for col_name in column_groups.keys():
                if col_name == "single":
                    db = find_d_option_table_bottom(page, None)
                else:
                    db = find_d_option_table_bottom(page, col_name)
                d_bottom_per_column[col_name] = db if db is not None else PAGE_HEIGHT_PT - FOOTER_PT

            # Render page with pymupdf
            doc_fitz = fitz.open(str(pdf_path))
            page_fitz = doc_fitz[page_idx]
            mat = fitz.Matrix(DPI / 72, DPI / 72)
            pix = page_fitz.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            
            sx = img.width / PAGE_WIDTH_PT
            sy = img.height / PAGE_HEIGHT_PT

            for column, col_anchors in column_groups.items():
                col_anchors.sort(key=lambda a: a["top"])
                crop_left, crop_right, scan_left, scan_right = bounds.get(column, bounds.get("single", (MARGIN_PT, PAGE_WIDTH_PT - MARGIN_PT, 0.0, PAGE_WIDTH_PT)))

                for idx, anchor in enumerate(col_anchors):
                    qnum = anchor["qnum"]
                    anchor_top = anchor["top"]

                    top = max(0.0, anchor_top - MARGIN_PT)

                    if idx + 1 < len(col_anchors):
                        next_limit = col_anchors[idx + 1]["top"] - MARGIN_PT
                    else:
                        next_limit = PAGE_HEIGHT_PT - FOOTER_PT

                    content_top = top

                    # Find D option just below this anchor, above next anchor
                    d_markers_in_col = []
                    for w in page.extract_words() or []:
                        text = str(w.get("text", "")).strip()
                        if text == "D)":
                            x0 = float(w["x0"])
                            dt = float(w["top"])
                            in_col = (column == "left" and x0 < COL_CENTER_PT) or (column == "right" and x0 >= COL_CENTER_PT) or (column == "single")
                            if in_col and dt > anchor_top + 10:
                                if idx + 1 < len(col_anchors):
                                    if dt < col_anchors[idx + 1]["top"] - 10:
                                        d_markers_in_col.append(dt)
                                else:
                                    d_markers_in_col.append(dt)

                    if d_markers_in_col:
                        d_top = min(d_markers_in_col)
                        # Find the bottom of the D option text (not just the marker)
                        # Look for all words in the same column below the D marker
                        d_bottom_text = d_top
                        for w in page.extract_words() or []:
                            w_top = float(w["top"])
                            w_x0 = float(w["x0"])
                            in_col = (column == "left" and w_x0 < COL_CENTER_PT) or (column == "right" and w_x0 >= COL_CENTER_PT) or (column == "single")
                            if in_col and w_top > d_top - 5 and w_top < PAGE_HEIGHT_PT - FOOTER_PT:
                                # Check if this word is below the D marker and not in footer
                                if w_top > d_top:
                                    d_bottom_text = max(d_bottom_text, w_top + 15)
                        bottom = min(PAGE_HEIGHT_PT, d_bottom_text + MARGIN_PT)
                    elif idx + 1 < len(col_anchors):
                        bottom = min(PAGE_HEIGHT_PT, next_limit)
                    else:
                        bottom = min(PAGE_HEIGHT_PT, PAGE_HEIGHT_PT - FOOTER_PT)

                    bottom = min(bottom, PAGE_HEIGHT_PT - 10)  # leave small margin at page bottom
                    
                    left = crop_left
                    right = crop_right

                    box = (round(left * sx), round(content_top * sy),
                           round(right * sx), round(bottom * sy))
                    
                    if box[2] <= box[0] or box[3] <= box[1]:
                        print(f"    WARNING: Invalid crop box for Q{qnum}: {box}")
                        continue

                    page_fitz = doc_fitz[page_idx]
                    mat = fitz.Matrix(DPI / 72, DPI / 72)
                    pix = page_fitz.get_pixmap(matrix=mat)
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    cropped = img.crop(box)
                    
                    if cropped.width == 0 or cropped.height == 0:
                        print(f"    WARNING: Empty crop for Q{qnum}")
                        continue
                    
                    # Filter out too-short crops (likely false positive anchors)
                    crop_height = box[3] - box[1]
                    if crop_height < 100:
                        print(f"    SKIP: Q{qnum} too short ({crop_height:.1f}pt), likely false positive")
                        continue

                    out_path = output_subdir / f"MEB-LGS-2015-{subject['slug'].upper()}-Q{qnum:02d}.png"
                    cropped.save(out_path, "PNG")

                    answer = answer_key.get(qnum)
                    if answer:
                        (output_subdir / f"MEB-LGS-2015-{subject['slug'].upper()}-Q{qnum:02d}.answer.txt").write_text(answer)

                    asset_hash = sha256(out_path)
                    h = bottom - content_top
                    print(f"    Q{qnum}: page={page_num} col={column} h={h:.1f}pt crop=({left:.1f},{content_top:.1f})-({right:.1f},{bottom:.1f})")

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
                            "assetSha256": sha256(out_path)
                        },
                        "answer": answer_key.get(qnum),
                        "status": "NEEDS_REVIEW",
                        "published": True,
                        "subject": subject["slug"]
                    })
                    extracted_qnums.add(qnum)

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

    # Copy to public/exams
    import shutil
    dst = REPO / "public" / "exams"
    dst.mkdir(parents=True, exist_ok=True)
    for slug, qs in all_questions_by_subject.items():
        for q in qs:
            src_png = OUTPUT_DIR / slug / f"MEB-LGS-2015-{slug.upper()}-Q{q['questionNumber']:02d}.png"
            if src_png.exists():
                target = REPO / "public" / "exams" / f"2015-{slug}-q{q['questionNumber']:02d}.png"
                shutil.copy2(src_png, target)

    print("\nTamamlandı!")


if __name__ == "__main__":
    main()