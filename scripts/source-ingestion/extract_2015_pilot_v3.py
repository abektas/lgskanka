#!/usr/bin/env python3
"""Fixed pilot - extract one question per subject correctly."""
import json
import hashlib
import re
from pathlib import Path
import fitz
from PIL import Image
import pdfplumber

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs 2015")
OUTPUT_DIR = REPO / "lgs_18_26" / "pilot_2015_v2"
DPI = 300
MARGIN_PT = 20.0
FOOTER_PT = 70.0
QUESTION_RE = re.compile(r"^(\d{1,2})\.$")

# Test questions per subject
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

PAGE_WIDTH_PT = 552.756
PAGE_HEIGHT_PT = 779.528


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def extract_one_question(subject_slug: str, test: dict) -> dict:
    """Extract a single question with proper cropping using D option table extent."""
    pdf_path = INPUT_DIR / test["pdf"]
    page_num = test["page"]
    qnum = test["qnum"]
    
    with pdfplumber.open(INPUT_DIR / test["pdf"]) as pdf:
        page = pdf.pages[test["page"] - 1]
        
        # Find D option position
        d_tops = []
        for w in page.extract_words() or []:
            text = str(w.get("text", "")).strip()
            if text == "D)":
                d_tops.append(float(w["top"]))
        
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
        
        # Find D option table extent - look for table content after D)
        # The D option table usually has header (Sporcu/Galibiyet) and data rows
        # Find the bottom of the D option table
        d_bottom = PAGE_HEIGHT_PT - FOOTER_PT  # default to page bottom
        if d_tops:
            d_top = max(d_tops)  # Use the D) marker position
            
            # Find table content below D) - look for table rows (Sporcu/Galibiyet/Mert etc.)
            # Use pdfplumber to find table elements after the D) marker
            for w in page.extract_words() or []:
                text = str(w.get("text", "")).strip()
                if text in ["Mert", "Sporcu", "Galibiyet", "Aydan", "Cansu", "Kerim"]:
                    w_top = float(w["top"])
                    if w_top > d_top:  # Only consider content below D)
                        d_bottom = max(d_bottom, w_top + 15)  # 15pt approx row height
            
            # Add margin
            d_bottom = min(d_bottom + MARGIN_PT, PAGE_HEIGHT_PT - FOOTER_PT)
        
        print(f"  Q{qnum}: D top={d_tops[0] if d_tops else 'N/A'} -> crop bottom={d_bottom:.1f}")
        
        # Calculate crop bounds
        if anchor["column"] == "left":
            left_pt, right_pt = MARGIN_PT, PAGE_WIDTH_PT / 2 - 5
        else:
            left_pt, right_pt = PAGE_WIDTH_PT / 2 + 5, PAGE_WIDTH_PT - MARGIN_PT
        
        top_pt = max(0, anchor["top"] - MARGIN_PT)
        
        # Render crop
        doc = fitz.open(str(INPUT_DIR / test["pdf"]))
        page_fitz = doc[test["page"] - 1]
        mat = fitz.Matrix(DPI/72, DPI/72)
        pix = page_fitz.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        
        sx = img.width / PAGE_WIDTH_PT
        sy = img.height / PAGE_HEIGHT_PT
        
        box = (
            round(left_pt * sx),
            round(top_pt * sy),
            round(right_pt * sx),
            round(d_bottom * sy)
        )
        
        # Determine left/right bounds based on column
        if anchor["column"] == "left":
            box = (round(MARGIN_PT * sx), round(top_pt * sy),
                   round((PAGE_WIDTH_PT/2 - 5) * sx), round(d_bottom * sy))
        else:
            box = (round((PAGE_WIDTH_PT/2 + 5) * sx), round(top_pt * sy),
                   round((PAGE_WIDTH_PT - MARGIN_PT) * sx), round(d_bottom * sy))
        
        cropped = img.crop(box)
        
        out_path = OUTPUT_DIR / f"{subject_slug}_Q{qnum}.png"
        cropped.save(out_path, "PNG")
        
        h = box[3] - box[1]
        w = box[2] - box[0]
        print(f"  {subject_slug} Q{qnum}: page={test['page']} col={anchor['column']} crop=({box[0]/sx:.1f},{box[1]/sy:.1f})-({box[2]/sx:.1f},{box[3]/sy:.1f}) px={w}x{h}")
        
        return {
            "subject": subject_slug,
            "qnum": qnum,
            "page": test["page"],
            "crop": box,
            "path": str(out_path)
        }


def main():
    OUTPUT_DIR = Path("/home/selam/roller/web/lgs-ai-coach/lgs_18_26/pilot_2015_v2")
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