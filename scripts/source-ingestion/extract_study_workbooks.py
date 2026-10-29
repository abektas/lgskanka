#!/usr/bin/env python3
"""
Extract questions from mixed LGS study workbooks PDFs.
Organizes by subject: turkce, matematik, fen-bilimleri, ingilizce, din-kulturu, inkilap-tarihi
"""
import re
import json
import hashlib
from pathlib import Path

import pdfplumber

INPUT_DIR = Path("/media/selam/Yeni Birim/lgs_çalışma_soruları")
OUTPUT_DIR = Path("/home/selam/.hermes/cache/scratch/lgs_study_all_subjects_20pt")

DPI = 300
MARGIN_PT = 20.0
FOOTER_PT = 70.0
QUESTION_RE = re.compile(r"^(\d{1,2})\.$")

SUBJECT_SLUGS = {
    "turkce": "turkce",
    "matematik": "matematik",
    "fen-bilimleri": "fen-bilimleri",
    "ingilizce": "ingilizce",
    "din-kulturu": "din-kulturu",
    "inkilap-tarihi": "inkilap-tarihi"
}

SUBJECT_HEADERS = {
    "turkce": ["türkçe soruları", "türkçe"],
    "matematik": ["matematik soruları", "matematik"],
    "fen-bilimleri": ["fen bilimleri soruları", "fen bilimleri"],
    "ingilizce": ["ingilizce soruları", "english questions", "ingilizce"],
    "inkilap-tarihi": ["t.c. inkilap", "inkılap tarihi", "atatürkçülük"],
    "din-kulturu": ["din kültürü", "ahlak bilgisi", "din kültürü ve ahlak"]
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def content_bbox(rendered, page, top_pt: float, limit_pt: float, x0_pt: float, x1_pt: float):
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

def detect_page_warning_top(page):
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
    if not words:
        return None
    lines = {}
    for w in words:
        top = round(float(w["top"]))
        lines.setdefault(top, []).append(w)
    warning_words = {"TEST", "BİTTİ", "GEÇİNİZ", "KONTROL", "EDİNİZ", "CEVAPLARINIZI", "DİĞERSAYFAYA", "GEÇİNİZ"}
    tops = []
    for top, line_words in lines.items():
        if top <= 450:
            continue
        full_text = " ".join(str(w.get("text", "")).strip().upper() for w in line_words)
        import re
        words_in_line = re.findall(r"[A-ZÇĞİÖŞÜ]+", full_text)
        if any(w in words_in_line for w in warning_words):
            tops.append(float(top))
    return min(tops) if tops else None

def extract_questions_from_page(page, page_num, current_subject, question_counters, pdf_path, all_questions):
    """Extract questions from a single page for the current subject"""
    if not current_subject:
        return []
    
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
        return []
    
    # Group by column
    left_anchors = [a for a in anchors if a[1] < page.width / 2]
    right_anchors = [a for a in anchors if a[1] >= page.width / 2]
    
    rendered = page.to_image(resolution=72).original.convert("RGB")
    divider_x = detect_center_divider_x(rendered, page)
    warning_top = detect_page_warning_top(page)
    
    # Determine bounds based on column structure
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
    
    specs = []
    rendered = page.to_image(resolution=72).original.convert("RGB")
    warning_top = detect_page_warning_top(page)
    
    for column, col_anchors in sorted(column_groups.items()):
        col_anchors.sort(key=lambda a: a[2])
        crop_left, crop_right, scan_left, scan_right = bounds.get(column, bounds.get("single", (MARGIN_PT, page.width - MARGIN_PT, 0.0, page.width)))
        
        for idx, (qnum, _x0, anchor_top) in enumerate(col_anchors):
            if qnum in question_counters[current_subject]:
                continue  # already processed
            
            top = max(0.0, anchor_top - MARGIN_PT)
            if page_num == 1 and top < 134.5:  # 2018/2019 instruction block handling
                top = 134.5
            
            if idx + 1 < len(col_anchors):
                next_limit = col_anchors[idx + 1][2] - MARGIN_PT
            elif warning_top is not None:
                next_limit = warning_top - MARGIN_PT
            else:
                next_limit = page.height - FOOTER_PT
            
            if warning_top is not None:
                next_limit = min(next_limit, warning_top - MARGIN_PT)
            
            bbox_scan_top = anchor_top
            bbox = content_bbox(rendered, page, bbox_scan_top, next_limit, 
                              bounds.get(column, bounds.get("single", (MARGIN_PT, page.width - MARGIN_PT, 0.0, page.width)))[2],
                              bounds.get(column, bounds.get("single", (MARGIN_PT, page.width - MARGIN_PT, 0.0, page.width)))[3])
            
            if bbox:
                content_top = max(top, bbox["y0"] - MARGIN_PT)
                if page_num > 1:
                    content_top = max(content_top, 80.0)
                bottom = min(float(page.height), next_limit, bbox["y1"] + MARGIN_PT)
                left = max(bounds.get(column, bounds.get("single", (MARGIN_PT, page.width - MARGIN_PT, 0.0, page.width)))[0], bbox["x0"] - MARGIN_PT)
                right = min(bounds.get(column, bounds.get("single", (MARGIN_PT, page.width - MARGIN_PT, 0.0, page.width)))[1], bbox["x1"] + MARGIN_PT)
            else:
                content_top, bottom, left, right = top, next_limit, bounds.get(column, bounds.get("single", (MARGIN_PT, page.width - MARGIN_PT, 0.0, page.width)))[0], bounds.get(column, bounds.get("single", (MARGIN_PT, page.width - MARGIN_PT, 0.0, page.width)))[1]
            
            specs.append({
                "question_number": qnum,
                "column": column,
                "rect_pt": {
                    "x0": round(left, 3),
                    "y0": round(content_top, 3),
                    "x1": round(right, 3),
                    "y1": round(bottom, 3)
                }
            })
    
    # Crop and save
    results = []
    image = page.to_image(resolution=DPI).original
    sx = image.width / float(page.width)
    sy = image.height / float(page.height)
    
    for spec in specs:
        if spec["question_number"] in question_counters[current_subject]:
            continue
        
        question_counters[current_subject].add(spec["question_number"])
        rect = spec["rect_pt"]
        box = (round(rect["x0"] * sx), round(rect["y0"] * sy), 
               round(rect["x1"] * sx), round(rect["y1"] * sy))
        
        # Validate crop box
        if box[2] <= box[0] or box[3] <= box[1]:
            print(f"  WARNING: Invalid crop box for Q{spec['question_number']}: {box}, skipping")
            continue
        
        out_path = OUTPUT_DIR / current_subject / f"q-{spec['question_number']:02d}.png"
        cropped = image.crop(box)
        if cropped.width == 0 or cropped.height == 0:
            print(f"  WARNING: Empty crop for Q{spec['question_number']}: {box}, skipping")
            continue
        cropped.save(out_path, "PNG")
        
        asset_hash = hashlib.sha256()
        with out_path.open("rb") as f:
            asset_hash.update(f.read())
        
        all_questions.append({
            "id": f"STUDY-{pdf_path.stem.upper()}-{current_subject.upper()}-Q{spec['question_number']:02d}",
            "questionNumber": spec["question_number"],
            "page": page_num,
            "column": spec["column"],
            "representation": "IMAGE_BACKED",
            "visual": {
                "publicPath": f"/study-{pdf_path.stem.lower()}-{current_subject}/q-{spec['question_number']:02d}.png",
                "clipRectPt": rect,
                "renderDpi": DPI,
                "authority": "ORIGINAL_MEB_PDF",
                "reconstructedFromOcr": False,
                "assetSha256": asset_hash.hexdigest()
            },
            "status": "NEEDS_REVIEW",
            "published": False,
            "subject": current_subject
        })
    return []

def process_pdf(pdf_path: Path):
    """Process a single PDF and extract questions by subject"""
    pdf_name = pdf_path.name
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Processing {pdf_path.name} ({len(pdf.pages)} pages)...")
        
        current_subject = None
        question_counters = {s: set() for s in ["turkce", "matematik", "fen-bilimleri", "ingilizce", "din-kulturu", "inkilap-tarihi"]}
        pdf_all_questions = []
        
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            
            # Detect subject
            detected = None
            lower = (page.extract_text() or "").lower()
            
            if "türkçe soruları" in lower or ("türkçe" in lower and "sorular" in lower):
                detected = "turkce"
            elif "matematik soruları" in lower:
                detected = "matematik"
            elif "fen bilimleri soruları" in lower:
                detected = "fen-bilimleri"
            elif "ingilizce soruları" in lower or "english questions" in lower:
                detected = "ingilizce"
            elif "t.c. inkilap" in lower or "inkılap tarihi" in lower or "atatürkçülük" in lower:
                detected = "inkilap-tarihi"
            elif "din kültürü" in lower or "ahlak bilgisi" in lower or "din kültürü ve ahlak" in lower:
                detected = "din-kulturu"
            
            if detected:
                current_subject = detected
                print(f"  Page {page_num}: Subject -> {detected}")
            
            if not current_subject:
                continue
            
            extract_questions_from_page(page, page_num, current_subject, question_counters, pdf_path, pdf_all_questions)
        
        print(f"  Total pages: {len(pdf.pages)}")
        return pdf_all_questions

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for s in ["turkce", "matematik", "fen-bilimleri", "ingilizce", "din-kulturu", "inkilap-tarihi"]:
        (OUTPUT_DIR / s).mkdir(parents=True, exist_ok=True)
    
    pdf_files = [
        "8ck1.pdf", "8ck2.pdf",
        "8mat_calisma.pdf", "8turk_calisma.pdf",
        "lgs_fen.pdf", "lgs_mat.pdf", "lgs_turkce.pdf",
        "lgs_soz_Türkçe.pdf", "lgs_soz_sosyal.pdf",
        "LGS 2027 - MEB Çalışma Kitabı -  Fen Bilimleri.pdf",
        "LGS 2027 - MEB Çalışma Kitabı -  Türkçe.pdf",
        "LGS 2027 - MEB MATEMATİK SORULARI - 1. DÖNEM.pdf",
        "LGS 2027 - MEB MATEMATİK SORULARI - 2. DÖNEM.pdf",
        "lgs_fen.pdf", "lgs_mat.pdf", "lgs_turkce.pdf",
        "lgs_soz_Türkçe.pdf", "lgs_soz_sosyal.pdf",
        "lgs_2023_ornek_1.pdf",
        "LGS Örnek Sorular  Sayısal Bölüm - Kasım 2025.pdf",
        "sozel_örnek sorular.pdf",
        "LGS 2027 - MEB MATEMATİK SORULARI - 2. DÖNEM.pdf",
        "LGS Örnek Sorular  Sayısal Bölüm - Kasım 2025.pdf",
        "sozel_örnek sorular.pdf",
    ]
    
    INPUT_DIR = Path("/media/selam/Yeni Birim/lgs_çalışma_soruları")
    all_questions = []
    
    for idx, fname in enumerate(pdf_files, 1):
        pdf_path = INPUT_DIR / fname
        if not pdf_path.exists():
            print(f"Skipping missing: {fname}")
            continue
        pdf_questions = process_pdf(pdf_path)
        all_questions.extend(pdf_questions)
    
    # Save manifest
    manifest = {
        "manifestVersion": "1.0",
        "status": "NEEDS_REVIEW",
        "published": False,
        "subjects": []
    }
    
    for subject in ["turkce", "matematik", "fen-bilimleri", "ingilizce", "din-kulturu", "inkilap-tarihi"]:
        subject_qs = [q for q in all_questions if q["subject"] == subject]
        subject_qs.sort(key=lambda q: q["questionNumber"])
        manifest["subjects"].append({
            "manifestVersion": "1.0",
            "status": "NEEDS_REVIEW",
            "published": False,
            "source": {
                "sourceId": f"STUDY-WORKBOOKS-{subject.upper()}",
                "sourceType": "STUDY_WORKBOOK",
                "subject": subject,
                "grade": 8,
            },
            "questions": subject_qs,
            "summary": {
                "questionsExtracted": len(subject_qs),
                "expectedQuestions": len(subject_qs)
            }
        })
    
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    total = sum(len([q for q in all_questions if q['subject']==s]) for s in ['turkce','matematik','fen-bilimleri','ingilizce','din-kulturu','inkilap-tarihi'])
    print(f"Done. Total questions: {total}")

if __name__ == "__main__":
    main()