#!/usr/bin/env python3
"""Simple pilot - test specific questions with correct anchor-based cropping."""
import json
import hashlib
import re
from pathlib import Path
import fitz
from PIL import Image
import pdfplumber

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs 2015")
OUTPUT_DIR = REPO / "lgs_18_26" / "pilot_2015"
DPI = 300
MARGIN_PT = 20.0
FOOTER_PT = 70.0
QUESTION_RE = re.compile(r"^(\d{1,2})\.$")

# Test questions per subject
PILOT_QUESTIONS = {
    "turkce": [1, 4, 7, 10, 14, 17, 20],
    "inkilap-tarihi": [1, 5, 10],
    "din-kulturu": [1, 5, 10],
    "ingilizce": [1, 5, 10],
    "matematik": [1, 5, 10, 15, 20],
    "fen-bilimleri": [1, 5, 10, 15, 20],
}

SOZEL_SUBJECTS = [
    {"slug": "turkce", "name": "Türkçe", "page_start": 3, "page_end": 10, "pdf": "2015 Sözel.pdf"},
    {"slug": "inkilap-tarihi", "name": "İnkılap", "page_start": 11, "page_end": 14, "pdf": "2015 Sözel.pdf"},
    {"slug": "din-kulturu", "name": "Din", "page_start": 15, "page_end": 17, "pdf": "2015 Sözel.pdf"},
    {"slug": "ingilizce", "name": "İngilizce", "page_start": 18, "page_end": 22, "pdf": "2015 Sözel.pdf"},
]
SAYISAL_SUBJECTS = [
    {"slug": "matematik", "name": "Matematik", "page_start": 3, "page_end": 11, "pdf": "2015 Sayısal.pdf"},
    {"slug": "fen-bilimleri", "name": "Fen", "page_start": 12, "page_end": 21, "pdf": "2015 Sayısal.pdf"},
]

DPI = 300
MARGIN_PT = 20.0
FOOTER_PT = 70.0
QUESTION_RE = re.compile(r"^(\d{1,2})\.$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def find_d_options(page):
    words = page.extract_words() or []
    d_options = []
    for w in words:
        text = str(w.get("text", "")).strip()
        if text == "D)":
            d_options.append(float(w["top"]))
    return d_options


def find_anchors_on_page(page, page_width, target_qnums):
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
    anchors = []
    for w in page.extract_words(use_text_flow=False, keep_blank_chars=False) or []:
        text = str(w.get("text", "")).strip()
        match = QUESTION_RE.fullmatch(text)
        if match:
            qnum = int(match.group(1))
            if qnum not in target_qnums:
                continue
            x0 = float(w["x0"])
            top = float(w["top"])
            if x0 <= 80 or page_width / 2 - 10 <= x0 <= page_width / 2 + 10:
                anchors.append({"qnum": qnum, "x0": x0, "top": top, "column": "left" if x0 < page_width / 2 else "right"})
    return anchors


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


def extract_single_question(pdf_path: Path, subject: dict, page_num: int, answer_key: dict[int, str], output_subdir: Path, target_qnums: list[int]) -> list[dict]:
    """Extract specific questions from a specific page."""
    questions = []
    page_idx = page_num - 1
    
    with pdfplumber.open(pdf_path) as pdf:
        if page_idx >= len(pdf.pages):
            return []
        page = pdf.pages[page_idx]
        
        # Find anchors for target questions
        anchors = []
        for w in page.extract_words(use_text_flow=False, keep_blank_chars=False) or []:
            text = str(w.get("text", "")).strip()
            match = QUESTION_RE.fullmatch(text)
            if match:
                qnum = int(match.group(1))
                if qnum not in target_qnums:
                    continue
                x0 = float(w["x0"])
                top = float(w["top"])
                if x0 <= 80 or page.width / 2 - 10 <= x0 <= page.width / 2 + 10:
                    anchors.append({"qnum": qnum, "x0": x0, "top": top, "column": "left" if x0 < page.width / 2 else "right"})
    
    if not anchors:
        return []
    
    # Get D options for this page
    with pdfplumber.open(pdf_path) as pdf_check:
        page = pdf_check.pages[page_idx]
        d_tops = find_d_options(page)
        d_bottom = max(d_tops) + MARGIN_PT if d_tops else page.height - FOOTER_PT
    
    # Group by column
    left_anchors = [a for a in anchors if a["column"] == "left"]
    right_anchors = [a for a in anchors if a["column"] == "right"]
    left_anchors.sort(key=lambda a: a["top"])
    right_anchors.sort(key=lambda a: a["top"])
    
    page_width = 552.756
    page_height = 779.528
    
    if left_anchors and right_anchors:
        column_groups = {"left": left_anchors, "right": right_anchors}
        bounds = {
            "left": (MARGIN_PT, page_width / 2 - 5, 0.0, page_width / 2 - 5),
            "right": (page_width / 2 + 5, page_width - MARGIN_PT, page_width / 2 + 5, page_width),
        }
    else:
        column_groups = {"single": anchors}
        bounds = {"single": (MARGIN_PT, 532.8 - MARGIN_PT, 0.0, 532.8)}
    
    # Render with pymupdf
    doc_fitz = fitz.open(str(pdf_path))
    page_fitz = doc_fitz[page_num - 1]
    mat = fitz.Matrix(DPI / 72, DPI / 72)
    pix = page_fitz.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    
    sx = img.width / float(552.756)
    sy = img.height / float(779.528)
    
    questions = []
    
    # Determine bottom for the page (max D option + margin)
    with pdfplumber.open(INPUT_DIR / (subject["pdf"])) as pdf_check:
        d_tops = find_d_options(pdf_check.pages[page_num - 1])
        d_bottom = max(d_tops) + MARGIN_PT if d_tops else 779.528 - FOOTER_PT
    
    for column, col_anchors in [("left", [a for a in anchors if a["column"] == "left"]), ("right", [a for a in anchors if a["column"] == "right"])]:
        if not col_anchors:
            continue
        col_anchors.sort(key=lambda a: a["top"])
        crop_left, crop_right, scan_left, scan_right = bounds.get(column, bounds.get("single", (MARGIN_PT, page_width - MARGIN_PT, 0.0, page_width)))
        
        for idx, anchor in enumerate(col_anchors):
            qnum = anchor["qnum"]
            anchor_top = anchor["top"]
            
            top = max(0.0, anchor_top - MARGIN_PT)
            
            # Find next anchor in same column
            if idx + 1 < len(col_anchors):
                next_limit = col_anchors[idx + 1]["top"] - MARGIN_PT
            else:
                next_limit = 779.528 - FOOTER_PT
            
            content_top = top
            bottom = min(779.528, next_limit)
            
            # Use D bottom for last question
            if idx + 1 >= len(col_anchors):
                bottom = max(bottom, d_bottom)
            
            left = bounds.get(column, bounds.get("single", (MARGIN_PT, 532.8 - MARGIN_PT, 0.0, 532.8)))[0]
            right = bounds.get(column, bounds.get("single", (MARGIN_PT, 532.8 - MARGIN_PT, 0.0, 532.8)))[1]
            
            box = (round(left * sx), round(content_top * sy),
                   round(right * sx), round(bottom * sy))
            
            if box[2] <= box[0] or box[3] <= box[1]:
                print(f"    WARNING: Invalid crop box for Q{qnum}: {box}")
                continue
            
            # Render crop
            doc_fitz = fitz.open(str(pdf_path))
            page_fitz = doc_fitz[page_num - 1]
            mat = fitz.Matrix(DPI / 72, DPI / 72)
            pix = page_fitz.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            cropped = img.crop(box)
            
            if cropped.width == 0 or cropped.height == 0:
                print(f"    WARNING: Empty crop for Q{qnum}")
                continue
            
            out_path = OUTPUT_DIR / subject["slug"] / f"MEB-LGS-2015-{subject['slug'].upper()}-Q{qnum:02d}.png"
            cropped.save(out_path, "PNG")
            
            answer = answer_key.get(qnum)
            if answer:
                (OUTPUT_DIR / subject["slug"] / f"MEB-LGS-2015-{subject['slug'].upper()}-Q{qnum:02d}.answer.txt").write_text(answer)
            
            asset_hash = sha256(out_path)
            h = bottom - content_top
            print(f"    Q{qnum}: page={page_num} col={anchor['column']} h={h:.1f}pt crop=({left:.1f},{content_top:.1f})-({right:.1f},{bottom:.1f})")
            
            return [{
                "id": f"MEB-LGS-2015-{subject['slug'].upper()}-Q{qnum:02d}",
                "questionNumber": qnum,
                "page": page_num,
                "column": anchor["column"],
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
            }]
    
    return []


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


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


def main():
    all_answers = parse_answer_key()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for subj in SOZEL_SUBJECTS + SAYISAL_SUBJECTS:
        (OUTPUT_DIR / subj["slug"]).mkdir(parents=True, exist_ok=True)
    
    pilot_qs = PILOT_QUESTIONS
    
    subjects = SOZEL_SUBJECTS + SAYISAL_SUBJECTS
    all_pilot = {}
    
    for subj in SOZEL_SUBJECTS + SAYISAL_SUBJECTS:
        pilot_qs_list = PILOT_QUESTIONS.get(subj["slug"], [])
        pdf_name = subj["pdf"]
        pdf_path = INPUT_DIR / pdf_name
        answer_key = parse_answer_key().get(subj["slug"], {})
        
        print(f"\n=== {subj['name']} Pilot ===")
        all_questions = []
        
        # Find which pages have our target questions
        with pdfplumber.open(INPUT_DIR / subj["pdf"]) as pdf:
            for page_idx in range(len(pdf.pages)):
                page = pdf.pages[page_idx]
                page_num = page_idx + 1
                anchors = []
                for w in page.extract_words(use_text_flow=False, keep_blank_chars=False) or []:
                    text = str(w.get("text", "")).strip()
                    match = re.match(r"^(\d{1,2})\.$", text)
                    if match:
                        qnum = int(match.group(1))
                        if qnum in PILOT_QUESTIONS[subj["slug"]]:
                            x0 = float(w["x0"])
                            top = float(w["top"])
                            if x0 <= 80 or page.width / 2 - 10 <= x0 <= page.width / 2 + 10:
                                print(f"  Found Q{qnum} on page {page_num} at top={top:.1f} x0={w['x0']:.1f}")
        
        # Extract each question
        all_qs = []
        for qnum in PILOT_QUESTIONS[subj["slug"]]:
            # Find page
            found_page = None
            with pdfplumber.open(INPUT_DIR / subj["pdf"]) as pdf:
                for page_idx in range(len(pdf.pages)):
                    page = pdf.pages[page_idx]
                    words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
                    for w in page.extract_words(use_text_flow=False, keep_blank_chars=False) or []:
                        text = str(w.get("text", "")).strip()
                        match = re.match(r"^(\d{1,2})\.$", text)
                        if match:
                            qnum = int(match.group(1))
                            if qnum == qnum:
                                found_page = page_idx + 1
                                break
                if found_page:
                    break
            
            if found_page:
                pdf_name = SOZEL_SUBJECTS[0]["pdf"] if subj in SOZEL_SUBJECTS else SAYISAL_SUBJECTS[0]["pdf"]
                pdf_path = INPUT_DIR / pdf_name
                ans_key = parse_answer_key().get(subj["slug"], {})
                qs = extract_single_question(INPUT_DIR / subj["pdf"], subj, found_page, parse_answer_key().get(subj["slug"], {}), OUTPUT_DIR / subj["slug"], [qnum])
                for q in qs:
                    print(f"  Q{qnum}: page={found_page} col={q['column']} done")
                    all_questions.append(q)
        
        all_pilot_questions[subj["slug"]] = all_questions
    
    print("\nPilot tamamlandı!")


if __name__ == "__main__":
    main()