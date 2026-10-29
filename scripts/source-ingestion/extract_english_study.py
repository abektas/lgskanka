#!/usr/bin/env python3
"""
Extract English questions from study workbooks with answer key matching.
Strategy:
1. Find "İngilizce Soruları" header
2. Extract each question with its number
3. Search for answer key: question bottom → page bottom → unit bottom → PDF end
4. Save answer with same name as question
"""
import re
import json
import hashlib
from pathlib import Path

import pdfplumber

INPUT_DIR = Path("/media/selam/Yeni Birim/lgs_çalışma_soruları")
OUTPUT_DIR = Path("/home/selam/.hermes/cache/scratch/lgs_study_english_20pt")

DPI = 300
MARGIN_PT = 20.0
FOOTER_PT = 70.0
QUESTION_RE = re.compile(r"^(\d{1,2})\.$")

# English subject header patterns (order matters - longer first)
ENGLISH_HEADERS = [
    "İngilizce Soruları",
    "İNGİLİZCE SORULARI",
    "İngilizce",
    "İNGİLİZCE",
    "English Questions",
    "ENGLISH QUESTIONS",
]

# Answer key header patterns
ANSWER_KEY_HEADERS = [
    "CEVAP ANAHTARI",
    "CEVAP ANAHTARLARI",
    "ANSWER KEY",
    "ANSWER KEYS",
    "CEVAPLAR",
]


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


def find_answer_key_in_region(page, region_top_pt: float, region_bottom_pt: float) -> dict[str, str] | None:
    """Search for answer key pattern in a vertical region of the page."""
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
    if not words:
        return None
    
    # Group words by line (top position)
    lines = {}
    for w in words:
        top = round(float(w["top"]))
        if region_top_pt <= top <= region_bottom_pt:
            lines.setdefault(top, []).append(w)
    
    # Look for answer key pattern: "1. A" or "1 - A" or "1) A" etc.
    answers = {}
    for top, line_words in sorted(lines.items()):
        full_text = " ".join(str(w.get("text", "")).strip() for w in line_words)
        # Match patterns like "1. A", "1 - A", "1) A", "1.A"
        matches = re.findall(r"(\d{1,2})\s*[\.\)\-]\s*([A-E])\b", full_text)
        for q_num, answer in matches:
            q_num = int(q_num)
            if 1 <= q_num <= 30 and answer not in answers.values():
                answers[q_num] = answer
    
    return answers if answers else None


def find_answer_key_on_page(page, page_num: int, pdf_pages: list) -> dict[str, str] | None:
    """Search for answer key on current page, then subsequent pages."""
    # First check current page
    page_height = float(page.height)
    
    # Strategy 1: Check bottom of current page (below last question)
    result = find_answer_key_in_region(page, page_height * 0.7, page_height - FOOTER_PT)
    if result:
        return result
    
    # Strategy 2: Check next pages (up to 3 pages ahead)
    for offset in range(1, min(4, len(pdf_pages) - page_num + 1)):
        next_page = pdf_pages[page_num - 1 + offset]
        result = find_answer_key_in_region(next_page, 0, float(next_page.height) - FOOTER_PT)
        if result:
            return result
    
    return None


def extract_english_from_pdf(pdf_path: Path) -> list[dict]:
    """Extract English questions from a single PDF."""
    questions = []
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Processing {pdf_path.name} ({total_pages} pages)...")
        
        # Find English section start
        english_start_page = None
        for i, page in enumerate(pdf.pages):
            txt = (page.extract_text() or "").lower()
            for header in ENGLISH_HEADERS:
                if header.lower() in txt:
                    english_start_page = i
                    print(f"  English section starts at page {i+1}")
                    break
            if english_start_page is not None:
                break
        
        if english_start_page is None:
            print(f"  No English section found")
            return questions
        
        # Extract questions from English section
        current_subject = "ingilizce"
        question_counters = set()
        
        for page_idx in range(english_start_page, total_pages):
            page = pdf.pages[page_idx]
            page_num = page_idx + 1
            page_text = page.extract_text() or ""
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
            
            # Check if we've left the English section (another subject header)
            lower = page_text.lower()
            other_subjects = ["türkçe soruları", "matematik soruları", "fen bilimleri soruları", 
                            "t.c. inkılap", "din kültürü", "cevap anahtarı"]
            if any(s in lower for s in other_subjects) and page_idx > english_start_page:
                # Check if it's really a new section (not just a mention)
                if any(s in lower for s in ["türkçe soruları", "matematik soruları", "fen bilimleri soruları"]):
                    print(f"  Left English section at page {page_num}")
                    break
            
            # Find question anchors
            anchors = []
            for w in words:
                text = str(w.get("text", "")).strip()
                match = re.match(r"^(\d{1,2})\.$", text)
                if match:
                    qnum = int(match.group(1))
                    x0 = float(w["x0"])
                    top = float(w["top"])
                    # Question numbers should be at left margin or center-left
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
                        print(f"  WARNING: Invalid crop box for Q{qnum}: {box}, skipping")
                        continue
                    
                    out_path = OUTPUT_DIR / "ingilizce" / f"q-{qnum:02d}.png"
                    cropped = image.crop(box)
                    if cropped.width == 0 or cropped.height == 0:
                        print(f"  WARNING: Empty crop for Q{qnum}: {box}, skipping")
                        continue
                    cropped.save(out_path, "PNG")
                    
                    # Find answer key
                    answer_key = find_answer_key_on_page(page, page_num, pdf.pages)
                    answer = answer_key.get(qnum) if answer_key else None
                    
                    # Save answer key if found
                    if answer:
                        answer_path = OUTPUT_DIR / "ingilizce" / f"q-{qnum:02d}.answer.txt"
                        answer_path.write_text(answer)
                        print(f"  Q{qnum}: answer={answer}")
                    else:
                        print(f"  Q{qnum}: answer=NOT_FOUND")
                    
                    asset_hash = hashlib.sha256()
                    with out_path.open("rb") as f:
                        asset_hash.update(f.read())
                    
                    questions.append({
                        "id": f"STUDY-{pdf_path.stem.upper()}-INGILIZCE-Q{qnum:02d}",
                        "questionNumber": qnum,
                        "page": page_num,
                        "column": column,
                        "representation": "IMAGE_BACKED",
                        "visual": {
                            "publicPath": f"/study-{pdf_path.stem.lower()}-ingilizce/q-{qnum:02d}.png",
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
                        "subject": "ingilizce"
                    })
        
        print(f"  Total pages: {total_pages}")
        return questions


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "ingilizce").mkdir(parents=True, exist_ok=True)
    
    # Process only 8ck PDFs (they have English sections)
    pdf_files = ["8ck1.pdf", "8ck2.pdf", "8ck3.pdf", "8ck4.pdf", "8ck5.pdf", "8ck6.pdf"]
    
    all_questions = []
    
    for fname in pdf_files:
        pdf_path = INPUT_DIR / fname
        if not pdf_path.exists():
            print(f"Skipping missing: {fname}")
            continue
        questions = extract_english_from_pdf(pdf_path)
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
                "sourceId": "STUDY-WORKBOOKS-INGILIZCE",
                "sourceType": "STUDY_WORKBOOK",
                "subject": "ingilizce",
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