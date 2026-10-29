#!/usr/bin/env python3
"""Fix matematik 2017 Q3,5,6,7,8,14,18,20 crops with correct bounds."""
import json
import hashlib
from pathlib import Path
import fitz
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs_2017")
DPI = 300
MARGIN_PT = 20.0
FOOTER_PT = 70.0

# Corrected bounds for Matematik from Sayısal PDF
# Page width = 552.756, center ≈ 276.4
FIXES = {
    "matematik": {
        # Page 4: Left col Q4 (anchor 98.7) to Q6 (anchor 418.4), Right col Q5 (anchor 98.7)
        4: {
            "page": 4,
            "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 418.4},  # Left col: Q4
            "column": "left"
        },
        5: {
            "page": 4,
            "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 371.4},  # Right col: Q5 (D at top=351.4)
            "column": "right"
        },
        6: {
            "page": 4,
            "clipRectPt": {"x0": 20.0, "y0": 398.4, "x1": 271.4, "y1": 672.8},  # Left col: Q6 (D at top=652.8)
            "column": "left"
        },
        # Page 5: Q7 (left, anchor 98.7) to Q8 (anchor 522.3)
        7: {
            "page": 5,
            "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 532.8, "y1": 516.7},  # Full width: Q7 (D at 496.7)
            "column": "single"
        },
        8: {
            "page": 5,
            "clipRectPt": {"x0": 20.0, "y0": 502.3, "x1": 532.8, "y1": 743.1},  # Full width: Q8 (D at 723.1)
            "column": "single"
        },
        # Page 7: Q14 (left), Q15 (left), Q16 (right), Q17 (right), Q18 (right)
        14: {
            "page": 7,
            "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 452.6},  # Left col: Q14 (D at 181.3 in right col... wait)
            "column": "left"
        },
        18: {
            "page": 7,
            "clipRectPt": {"x0": 281.4, "y0": 432.6, "x1": 532.8, "y1": 727.8},  # Right col: Q18 (D at 707.8)
            "column": "right"
        },
        20: {
            "page": 8,
            "clipRectPt": {"x0": 20.0, "y0": 379.1, "x1": 532.8, "y1": 684.2},  # Q20 (D at 664.2)
            "column": "single"
        },
    },
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def re_crop_question(pdf_path: Path, subj: str, qnum: int, fix: dict, output_dir: Path):
    page_idx = fix["page"] - 1
    clip = fix["clipRectPt"]
    
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
    
    old_path = output_dir / f"MEB-LGS-2017-{subj.upper()}-Q{qnum:02d}.png"
    if old_path.exists():
        old_path.rename(output_dir / f"MEB-LGS-2017-{subj.upper()}-Q{qnum:02d}.png.bak4")
    
    cropped.save(old_path, "PNG")
    asset_hash = sha256(old_path)
    print(f"  Fixed {subj} Q{qnum}: page={fix['page']} crop=({clip['x0']:.1f},{clip['y0']:.1f})-({clip['x1']:.1f},{clip['y1']:.1f}) hash={asset_hash[:16]}...")
    return True


def update_manifest(subj: str, qnum: int, fix: dict):
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
    pdf_sayisal = INPUT_DIR / "2017 Sayısal.pdf"
    output_dir = REPO / "lgs_18_26" / "matematik"
    
    for qnum, fix in FIXES["matematik"].items():
        re_crop_question(pdf_sayisal, "matematik", qnum, fix, output_dir)
        update_manifest("matematik", qnum, fix)
    
    # Copy to public/exams
    import shutil, re
    dst = REPO / "public" / "exams"
    for qnum in FIXES["matematik"].keys():
        src_png = output_dir / f"MEB-LGS-2017-MATEMATIK-Q{qnum:02d}.png"
        target = dst / f"2017-matematik-q{qnum:02d}.png"
        if src_png.exists():
            shutil.copy2(src_png, target)
            print(f"  Copied: {target.name}")
    
    print("Tamamlandı!")


if __name__ == "__main__":
    main()