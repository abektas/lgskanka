#!/usr/bin/env python3
"""
Extract Fen Bilimleri questions from cal09.pdf with answer key matching.
Uses pdfplumber word coordinates to detect column positions.
"""
import re
import json
import hashlib
from pathlib import Path

import pdfplumber

INPUT_DIR = Path("/media/selam/Yeni Birim/lgs_çalışma_soruları")
OUTPUT_DIR = Path("/home/selam/.hermes/cache/scratch/lgs_study_fen_20pt")

DPI = 300
MARGIN_PT = 20.0
FOOTER_PT = 70.0
QUESTION_RE = re.compile(r"^(\d{1,2})\.$")

# Subject header patterns
FEN_HEADERS = ["Fen Bilimleri Soruları", "FEN BİLİMLERİ SORULARI"]
ANSWER_KEY_HEADERS = ["CEVAP ANAHTARI", "CEVAP ANAHTARLARI"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def content_bbox(rendered, page, top_pt: float, limit_pt: float, x0_pt: float, x1_pt: float):
    """Find content bounding box in the given region."""
    scale = rendered.width / float(page.width)
    y_start = max(0, int(top_pt * scale))
    y_end = min(rendered.height - 1, int(limit_pt * scale))
    x_start = max(0, int(x0_pt * scale))
    x_end = min(rendered.width, int(x1_pt * scale))
    pixels = rendered.load()
    rows = []
    for y in range(y_start, y_end + 1):
        occupied = 0
        for x in range(x_start, x_end):
            r, g, b = pixels[x, y][:3]
            if min(r, g, b) < 245:
                occupied += 1
        if occupied >= 2:
            rows.append(y)
    if not rows:
        return None
    y0, y1 = min(rows), max(rows)
    cols = []
    for x in range(x_start, x_end):
        occupied = 0
        for y in range(y0, y1 + 1):
            r, g, b = pixels[x, y][:3]
            if min(r, g, b) < 245:
                occupied += 1
                if occupied >= 2:
                    cols.append(x)
                    break
    if not cols:
        return None
    return {
        "x0": min(cols) / scale,
        "y0": y0 / scale,
        "x1": (max(cols) + 1) / scale,
        "y1": (y1 + 1) / scale,
    }


def detect_center_divider_x(rendered, page):
    """Detect vertical divider between two columns."""
    scale = rendered.width / float(page.width)
    center = int((page.width / 2) * scale)
    best = None
    for x in range(max(0, center - int(20 * scale)), min(rendered.width, center + int(40 * scale))):
        colored = 0
        for y in range(rendered.height):
            r, g, b = rendered.getpixel((x, y))
            if max(r, g, b) - min(r, g, b) > 55 and min(r, g, b) < 220:
                colored += 1
        if best is None or colored > best[1]:
            best = (x, colored)
    if best and best[1] >= rendered.height * 0.20:
        return best[0] / scale
    return None


def find_fen_column_x(page) -> float | None:
    """Find the x0 position of the FEN BİLİMLERİ column on an answer key page.
    The header may be split across multiple words (e.g. "FEN" at x0=418,
    "BİLİMLERİ" at x0=448). We look for the word "FEN" and return its x0."""
    words = page.extract_words()
    for w in words:
        text = w.get("text", "").strip().upper()
        if text == "FEN" or (text.startswith("FEN") and "BİLİMLERİ" not in text):
            return float(w["x0"])
    # Fallback: check for combined "FEN BİLİMLERİ" in a single word
    for w in words:
        text = w.get("text", "").strip().upper()
        if "FEN" in text and "BİLİMLERİ" in text:
            return float(w["x0"])
    return None


def extract_fen_answers_from_key_page(page, fen_x0: float) -> dict[int, str]:
    """Extract Fen answers from answer key page using column position."""
    words = page.extract_words()
    answers = {}
    
    # Group words by line (top position)
    lines = {}
    for w in words:
        top = round(float(w["top"]))
        lines.setdefault(top, []).append(w)
    
    for top, line_words in sorted(lines.items()):
        # Sort by x0
        line_words.sort(key=lambda w: float(w["x0"]))
        
        # Find question number and answer in the Fen column region
        for i, w in enumerate(line_words):
            text = str(w.get("text", "")).strip()
            x0 = float(w["x0"])
            
            # Check if this word is in the Fen column (x0 >= fen_x0 - 20)
            if x0 < fen_x0 - 20:
                continue
            
            # Match question number
            match = re.match(r"^(\d{1,2})\.$", text)
            if match:
                qnum = int(match.group(1))
                # Look for answer in next few words
                for j in range(i + 1, min(i + 4, len(line_words))):
                    next_text = str(line_words[j].get("text", "")).strip()
                    if re.match(r"^[A-E]$", next_text):
                        answers[qnum] = next_text
                        break
    
    return answers


def extract_fen_from_pdf(pdf_path: Path) -> list[dict]:
    """Extract Fen Bilimleri questions from a single PDF."""
    questions = []
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Processing {pdf_path.name} ({total_pages} pages)...")
        
        # Find all Fen sections and answer key pages
        fen_sections = []  # (start_page, end_page) tuples
        answer_key_pages = []  # page numbers
        
        for i, page in enumerate(pdf.pages):
            txt = (page.extract_text() or "").lower()
            for header in FEN_HEADERS:
                if header.lower() in txt:
                    fen_sections.append(i)
                    print(f"  Fen section starts at page {i+1}")
                    break
            for header in ANSWER_KEY_HEADERS:
                if header.lower() in txt:
                    answer_key_pages.append(i)
                    print(f"  Answer key at page {i+1}")
                    break
        
        if not fen_sections:
            print(f"  No Fen sections found")
            return questions
        
        # Extract answers from all answer key pages
        all_answers = {}
        for key_page_idx in answer_key_pages:
            key_page = pdf.pages[key_page_idx]
            fen_x0 = find_fen_column_x(key_page)
            if fen_x0 is not None:
                answers = extract_fen_answers_from_key_page(key_page, fen_x0)
                all_answers.update(answers)
                print(f"  Found {len(answers)} Fen answers on page {key_page_idx+1}")
        
        # Extract questions from each Fen section
        for section_idx, section_start in enumerate(fen_sections):
            # Find section end (next Fen section or answer key or end of PDF)
            section_end = total_pages
            for next_start in fen_sections[section_idx + 1:]:
                section_end = min(section_end, next_start)
            for key_page in answer_key_pages:
                if key_page > section_start:
                    section_end = min(section_end, key_page)
            
            print(f"  Section {section_idx+1}: pages {section_start+1}-{section_end}")
            
            question_counters = set()
            
            for page_idx in range(section_start, section_end):
                page = pdf.pages[page_idx]
                page_num = page_idx + 1
                page_text = page.extract_text() or ""
                words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
                
                # Find question anchors
                anchors = []
                for w in words:
                    text = str(w.get("text", "")).strip()
                    match = re.match(r"^(\d{1,2})\.$", text)
                    if match:
                        qnum = int(match.group(1))
                        x0 = float(w["x0"])
                        top = float(w["top"])
                        if x0 <= 80 or page.width / 2 - 5 <= x0 <= page.width / 2 + 55:
                            anchors.append((qnum, x0, top))
                
                if not anchors:
                    continue
                
                # Group by column
                left_anchors = [a for a in anchors if a[1] < page.width / 2]
                right_anchors = [a for a in anchors if a[1] >= page.width / 2]
                
                rendered = page.to_image(resolution=72).original.convert("RGB")
                divider_x = detect_center_divider_x(rendered, page)
                
                # Determine bounds
                if left_anchors and right_anchors:
                    bounds = {
                        "left": (MARGIN_PT, page.width / 2 + MARGIN_PT, 0.0, page.width / 2),
                        "right": (page.width / 2 - MARGIN_PT, page.width - MARGIN_PT, page.width / 2 + 10.0, page.width),
                    }
                    if divider_x is not None:
                        bounds["left"] = (bounds["left"][0], min(bounds["left"][1], divider_x - 5.0), 
                                        bounds["left"][2], min(bounds["left"][3], divider_x - 5.0))
                        bounds["right"] = (max(bounds["right"][0], divider_x + 5.0), bounds["right"][1],
                                          max(bounds["right"][2], divider_x + 5.0), bounds["right"][3])
                    column_groups = {"left": left_anchors, "right": right_anchors}
                else:
                    bounds = {"single": (MARGIN_PT, page.width - MARGIN_PT, 0.0, page.width)}
                    column_groups = {"single": [a for a in anchors if a[1] < page.width / 2] + 
                                          [a for a in anchors if a[1] >= page.width / 2]}
                
                # Process each question
                for column, col_anchors in sorted(column_groups.items()):
                    col_anchors.sort(key=lambda a: a[2])
                    crop_left, crop_right, scan_left, scan_right = bounds.get(column, bounds.get("single", (MARGIN_PT, page.width - MARGIN_PT, 0.0, page.width)))
                    
                    for idx, (qnum, _x0, anchor_top) in enumerate(col_anchors):
                        if qnum in question_counters:
                            continue
                        
                        question_counters.add(qnum)
                        
                        # Calculate crop region
                        top = max(0.0, anchor_top - MARGIN_PT)
                        
                        if idx + 1 < len(col_anchors):
                            next_limit = col_anchors[idx + 1][2] - MARGIN_PT
                        else:
                            next_limit = page.height - FOOTER_PT
                        
                        # Find content bbox
                        bbox = content_bbox(rendered, page, anchor_top, next_limit, scan_left, scan_right)
                        
                        if bbox:
                            content_top = max(top, bbox["y0"] - MARGIN_PT)
                            if page_num > 1:
                                content_top = max(content_top, 80.0)
                            bottom = min(float(page.height), next_limit, bbox["y1"] + MARGIN_PT)
                            left = max(bounds.get(column, bounds.get("single", (MARGIN_PT, page.width - MARGIN_PT, 0.0, page.width)))[0], bbox["x0"] - MARGIN_PT)
                            right = min(bounds.get(column, bounds.get("single", (MARGIN_PT, page.width - MARGIN_PT, 0.0, page.width)))[1], bbox["x1"] + MARGIN_PT)
                        else:
                            content_top, bottom, left, right = top, next_limit, bounds.get(column, bounds.get("single", (MARGIN_PT, page.width - MARGIN_PT, 0.0, page.width)))[0], bounds.get(column, bounds.get("single", (MARGIN_PT, page.width - MARGIN_PT, 0.0, page.width)))[1]
                        
                        # Crop and save
                        image = page.to_image(resolution=DPI).original
                        sx = image.width / float(page.width)
                        sy = image.height / float(page.height)
                        
                        box = (round(left * sx), round(content_top * sy), 
                               round(right * sx), round(bottom * sy))
                        
                        if box[2] <= box[0] or box[3] <= box[1]:
                            print(f"    WARNING: Invalid crop box for Q{qnum}: {box}, skipping")
                            continue
                        
                        out_path = OUTPUT_DIR / "fen-bilimleri" / f"q-{qnum:02d}.png"
                        cropped = image.crop(box)
                        if cropped.width == 0 or cropped.height == 0:
                            print(f"    WARNING: Empty crop for Q{qnum}: {box}, skipping")
                            continue
                        cropped.save(out_path, "PNG")
                        
                        # Get answer from pre-extracted answers
                        answer = all_answers.get(qnum)
                        
                        # Save answer key if found
                        if answer:
                            answer_path = OUTPUT_DIR / "fen-bilimleri" / f"q-{qnum:02d}.answer.txt"
                            answer_path.write_text(answer)
                            print(f"    Q{qnum}: answer={answer}")
                        else:
                            print(f"    Q{qnum}: answer=NOT_FOUND")
                        
                        asset_hash = hashlib.sha256()
                        with out_path.open("rb") as f:
                            asset_hash.update(f.read())
                        
                        questions.append({
                            "id": f"STUDY-{pdf_path.stem.upper()}-FEN-BILIMLERI-Q{qnum:02d}",
                            "questionNumber": qnum,
                            "page": page_num,
                            "column": column,
                            "representation": "IMAGE_BACKED",
                            "visual": {
                                "publicPath": f"/study-{pdf_path.stem.lower()}-fen-bilimleri/q-{qnum:02d}.png",
                                "clipRectPt": {
                                    "x0": round(left, 3),
                                    "y0": round(content_top, 3),
                                    "x1": round(right, 3),
                                    "y1": round(bottom, 3)
                                },
                                "renderDpi": DPI,
                                "authority": "ORIGINAL_MEB_PDF",
                                "reconstructedFromOcr": False,
                                "assetSha256": asset_hash.hexdigest()
                            },
                            "answer": answer,
                            "status": "NEEDS_REVIEW",
                            "published": False,
                            "subject": "fen-bilimleri"
                        })
        
        print(f"  Total pages: {total_pages}")
        return questions


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "fen-bilimleri").mkdir(parents=True, exist_ok=True)
    
    pdf_files = ["cal09.pdf"]
    
    all_questions = []
    
    for fname in pdf_files:
        pdf_path = INPUT_DIR / fname
        if not pdf_path.exists():
            print(f"Skipping missing: {fname}")
            continue
        questions = extract_fen_from_pdf(pdf_path)
        all_questions.extend(questions)
    
    # Save manifest
    manifest = {
        "manifestVersion": "1.0",
        "status": "NEEDS_REVIEW",
        "published": False,
        "subjects": [{
            "manifestVersion": "1.0",
            "status": "NEEDS_REVIEW",
            "published": False,
            "source": {
                "sourceId": "STUDY-WORKBOOKS-FEN-BILIMLERI",
                "sourceType": "STUDY_WORKBOOK",
                "subject": "fen-bilimleri",
                "grade": 8,
            },
            "questions": all_questions,
            "summary": {
                "questionsExtracted": len(all_questions),
                "expectedQuestions": len(all_questions)
            }
        }]
    }
    
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"\nDone. Total questions: {len(all_questions)}")


if __name__ == "__main__":
    main()