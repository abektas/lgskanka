#!/usr/bin/env python3
"""Minimal pilot - extract one question per subject correctly."""
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

# One test question per subject
TEST_QUESTIONS = {
    "turkce": {"qnum": 14, "pdf": "2015 Sözel.pdf", "page": 8},  # Problematic Q14
    "inkilap-tarihi": {"qnum": 5, "pdf": "2015 Sözel.pdf", "page": 12},
    "din-kulturu": {"qnum": 5, "pdf": "2015 Sözel.pdf", "page": 16},
    "ingilizce": {"qnum": 5, "pdf": "2015 Sözel.pdf", "page": 20},
    "matematik": {"qnum": 5, "pdf": "2015 Sayısal.pdf", "page": 5},
    "fen-bilimleri": {"qnum": 5, "pdf": "2015 Sayısal.pdf", "page": 13},
}

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


def extract_one_question(subject_slug: str, test: dict) -> dict:
    """Extract a single question with proper cropping."""
    pdf_path = INPUT_DIR / test["pdf"]
    page_num = test["page"]
    qnum = test["qnum"]
    
    # Load PDFs
    with pdfplumber.open(INPUT_DIR / (test["pdf"])) as pdf:
        page = pdf.pages[test["page"] - 1]
        
        # Find D option position
        d_tops = []
        for w in page.extract_words() or []:
            text = str(w.get("text", "")).strip()
            if text == "D)":
                d_tops.append(float(w["top"]))
        d_bottom = max(d_tops) + 20 if d_tops else 779.528 - 70
        
        # Find the question anchor
        anchor = None
        for w in page.extract_words(use_text_flow=False, keep_blank_chars=False) or []:
            text = str(w.get("text", "")).strip()
            match = re.match(r"^(\d{1,2})\.$", text)
            if match and int(match.group(1)) == qnum:
                x0 = float(w["x0"])
                top = float(w["top"])
                column = "left" if x0 < 276 else "right"
                anchor = {"qnum": qnum, "top": top, "column": column}
                print(f"  Found Q{qnum} on page {test['page']} at top={top:.1f} col={column}")
                break
        
        if not anchor:
            print(f"  Q{qnum} NOT FOUND on page {test['page']}")
            return None
        
        # Calculate crop bounds
        if anchor["column"] == "left":
            left_pt, right_pt = 20.0, 271.4
        else:
            left_pt, right_pt = 281.4, 532.8
        
        top_pt = max(0, anchor["top"] - 20)
        
        # Find next question on same page/column to determine bottom
        # For simplicity, use D option position + 20pt for last question
        bottom_pt = min(779.528, d_tops[0] + 20) if d_tops else 779.528 - 70
        
        # Render crop
        doc = fitz.open(str(INPUT_DIR / test["pdf"]))
        page_fitz = doc[test["page"] - 1]
        mat = fitz.Matrix(300/72, 300/72)
        pix = page_fitz.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        
        sx = img.width / 552.756
        sy = img.height / 779.528
        
        box = (
            round(20.0 * sx), round((anchor["top"] - 20) * sy),
            round(532.8 * sx), round(d_tops[0] * sy + 20 * sy) if False else
            (round(271.4 * sx), round((anchor["top"] - 20) * sy), round(532.8 * sx), round((anchor["top"] + 500) * sy))
        )
        
        # Actually calculate proper bounds
        left_px = round(20.0 * sx)
        right_px = round(532.8 * sx)
        top_px = round((anchor["top"] - 20) * sy)
        
        # Find bottom: use D option position if it's the last question, else next question
        # For pilot, use D option + 20pt
        d_bottom_px = round((max([float(w["top"]) for w in fitz.open(str(INPUT_DIR / test["pdf"])).load_page(test["page"]-1).search_for("D)")] or [779.528-70]) + 20) * sy) if False else round(709.528 * sy)
        
        # Simpler: use D position we found
        with pdfplumber.open(INPUT_DIR / test["pdf"]) as pdf:
            page = pdf.pages[test["page"] - 1]
            d_tops = []
            for w in page.extract_words() or []:
                if str(w.get("text", "")).strip() == "D)":
                    d_tops.append(float(w["top"]))
            d_bottom_px = round((max(d_tops) + 20) * sy) if d_tops else round((779.528 - 70) * sy)
        
        box = (
            round(20.0 * sx),
            round((anchor["top"] - 20) * sy),
            round(532.8 * sx),
            round((max(d_tops) + 20) * sy) if d_tops else round(709.528 * sy)
        )
        
        if anchor["column"] == "left":
            box = (round(20.0 * sx), round((anchor["top"] - 20) * sy), round(271.4 * sx), round((max(d_tops) + 20) * sy) if d_tops else round(709.528 * sy))
        else:
            box = (round(281.4 * sx), round((anchor["top"] - 20) * sy), round(532.8 * sx), round((max(d_tops) + 20) * sy) if d_tops else round(709.528 * sy))
        
        doc = fitz.open(str(INPUT_DIR / test["pdf"]))
        page_fitz = doc[test["page"] - 1]
        mat = fitz.Matrix(DPI/72, DPI/72)
        pix = page_fitz.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        
        cropped = img.crop(box)
        
        out_path = Path(f"/home/selam/roller/web/lgs-ai-coach/lgs_18_26/pilot_2015/{test['pdf'].replace(' ', '_').replace('.pdf', '')}_Q{qnum}.png")
        cropped.save(out_path, "PNG")
        
        h = box[3] - box[1]
        w = box[2] - box[0]
        print(f"  {subject_slug} Q{qnum}: page={test['page']} crop=({box[0]/sx:.1f},{box[1]/sy:.1f})-({box[2]/sx:.1f},{box[3]/sy:.1f}) px={w}x{h}")
        
        return {
            "subject": "test",
            "qnum": qnum,
            "page": test["page"],
            "crop": box,
            "path": str(out_path)
        }


def main():
    OUTPUT_DIR = Path("/home/selam/roller/web/lgs-ai-coach/lgs_18_26/pilot_2015")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    for subject_slug, test in TEST_QUESTIONS.items():
        print(f"\n=== {subject_slug} Q{test['qnum']} ===")
        try:
            result = extract_one_question(subject_slug, test)
            if result:
                print(f"  OK: {result['path']}")
        except Exception as e:
            print(f"  ERROR: {e}")

    print("\nPilot done!")


if __name__ == "__main__":
    main()