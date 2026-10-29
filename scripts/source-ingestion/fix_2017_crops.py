#!/usr/bin/env python3
"""Fix specific miscropped questions from 2017."""
import json
import re
import hashlib
from pathlib import Path
import fitz
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs_2017")
DPI = 300
MARGIN_PT = 20.0
FOOTER_PT = 70.0

# Manual corrections: {subject: {qnum: {page, clipRectPt, column}}}
FIXES = {
    "matematik": {
        3:  {"page": 4, "clipRectPt": {"x0": 20.0, "y0": 78.0, "x1": 271.4, "y1": 418.0}, "column": "left"},
        5:  {"page": 4, "clipRectPt": {"x0": 281.4, "y0": 78.0, "x1": 532.8, "y1": 418.0}, "column": "right"},
        6:  {"page": 4, "clipRectPt": {"x0": 20.0, "y0": 398.4, "x1": 271.4, "y1": 709.5}, "column": "left"},
        7:  {"page": 5, "clipRectPt": {"x0": 20.0, "y0": 78.0, "x1": 532.8, "y1": 502.3}, "column": "single"},
        8:  {"page": 5, "clipRectPt": {"x0": 20.0, "y0": 502.3, "x1": 532.8, "y1": 709.5}, "column": "single"},
        14: {"page": 7, "clipRectPt": {"x0": 20.0, "y0": 78.0, "x1": 271.4, "y1": 709.5}, "column": "left"},
        18: {"page": 7, "clipRectPt": {"x0": 281.4, "y0": 432.6, "x1": 532.8, "y1": 709.5}, "column": "right"},
        20: {"page": 8, "clipRectPt": {"x0": 20.0, "y0": 379.1, "x1": 532.8, "y1": 709.5}, "column": "left"},
    },
    "fen-bilimleri": {
        14: {"page": 15, "clipRectPt": {"x0": 20.0, "y0": 78.0, "x1": 532.8, "y1": 709.5}, "column": "single"},
        16: {"page": 16, "clipRectPt": {"x0": 20.0, "y0": 78.0, "x1": 532.8, "y1": 709.5}, "column": "single"},
    },
    "inkilap-tarihi": {
        8: {"page": 13, "clipRectPt": {"x0": 281.4, "y0": 408.9, "x1": 532.8, "y1": 709.5}, "column": "right"},
    },
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def re_crop_question(pdf_path: Path, subj: str, qnum: int, fix: dict, output_dir: Path):
    """Re-crop a single question with corrected bounds."""
    page_idx = fix["page"] - 1
    clip = fix["clipRectPt"]
    column = fix.get("column", "single")
    
    doc = fitz.open(str(pdf_path))
    page = doc[page_idx]
    
    mat = fitz.Matrix(DPI / 72, DPI / 72)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    
    sx = img.width / float(page.rect.width)
    sy = img.height / float(page.rect.height)
    
    box = (round(clip["x0"] * sx), round(clip["y0"] * sy),
           round(clip["x1"] * sx), round(clip["y1"] * sy))
    
    cropped = img.crop(box)
    if cropped.width == 0 or cropped.height == 0:
        print(f"  ERROR: Empty crop for {subj} Q{qnum}")
        return False
    
    # Backup old file
    old_path = output_dir / f"MEB-LGS-2017-{subj.upper()}-Q{qnum:02d}.png"
    if old_path.exists():
        old_path.rename(output_dir / f"MEB-LGS-2017-{subj.upper()}-Q{qnum:02d}.png.bak")
    
    cropped.save(old_path, "PNG")
    asset_hash = sha256(old_path)
    print(f"  Fixed {subj} Q{qnum}: crop=({clip['x0']:.1f},{clip['y0']:.1f})-({clip['x1']:.1f},{clip['y1']:.1f}) hash={asset_hash[:16]}...")
    return True


def update_manifest(subj: str, qnum: int, fix: dict):
    """Update manifest with corrected clipRectPt."""
    manifest_path = REPO / "lgs_18_26" / subj / "manifest_2017.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    for q in manifest["questions"]:
        if q["questionNumber"] == qnum:
            q["visual"]["clipRectPt"] = fix["clipRectPt"]
            q["page"] = fix["page"]
            break
    
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  Manifest updated: {subj} Q{qnum}")


def main():
    # Fix matematik (Sayısal PDF)
    pdf_sayisal = INPUT_DIR / "2017 Sayısal.pdf"
    for subj in ["matematik", "fen-bilimleri"]:
        pdf_path = pdf_sayisal if subj == "matematik" else INPUT_DIR / "2017 Sözel.pdf"
        output_dir = REPO / "lgs_18_26" / subj
        
        if subj in FIXES:
            for qnum, fix in FIXES[subj].items():
                re_crop_question(pdf_path, subj, qnum, fix, output_dir)
                update_manifest(subj, qnum, fix)
    
    # Fix inkilap-tarihi (Sözel PDF)
    pdf_sozel = INPUT_DIR / "2017 Sözel.pdf"
    output_dir = REPO / "lgs_18_26" / "inkilap-tarihi"
    for qnum, fix in FIXES["inkilap-tarihi"].items():
        re_crop_question(pdf_sozel, "inkilap-tarihi", qnum, fix, output_dir)
        update_manifest("inkilap-tarihi", qnum, fix)
    
    print("\nTamamlandı! Kopyalama public/exams'e...")


if __name__ == "__main__":
    main()