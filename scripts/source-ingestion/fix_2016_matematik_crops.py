#!/usr/bin/env python3
"""Fix 2016 matematik crops - proper 20pt margins from content bounds."""
import json
import hashlib
from pathlib import Path
import fitz
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs_2016")
DPI = 300
MARGIN_PT = 20.0

# Corrected bounds for 2016 Matematik from Sayısal PDF
# Based on D option positions + 20pt margin
# Page width = 552.756, center ≈ 276.4
FIXES = {
    "matematik": {
        # Page 3 (index 2): Q1 left (D at top=315.3), Q3 left (D at top=662.7), Q2 right (D at top=208.2)
        1: {"page": 3, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 335.3}, "column": "left"},
        3: {"page": 3, "clipRectPt": {"x0": 20.0, "y0": 436.2, "x1": 271.4, "y1": 682.7}, "column": "left"},
        2: {"page": 3, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 228.2}, "column": "right"},
        
        # Page 4 (index 3): Q4 left (D at top=389.9), Q5 left (D at top=629.7), Q6 right (D at top=467.3)
        4: {"page": 4, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 409.9}, "column": "left"},
        5: {"page": 4, "clipRectPt": {"x0": 20.0, "y0": 400.2, "x1": 271.4, "y1": 649.7}, "column": "left"},
        6: {"page": 4, "clipRectPt": {"x0": 281.4, "y0": 400.7, "x1": 532.8, "y1": 487.3}, "column": "right"},
        
        # Page 5 (index 4): Q7 full (D at top=347.2), Q8 full (D at top=685.3)
        7: {"page": 5, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 532.8, "y1": 367.2}, "column": "single"},
        8: {"page": 5, "clipRectPt": {"x0": 20.0, "y0": 388.4, "x1": 532.8, "y1": 705.3}, "column": "single"},
        
        # Page 6 (index 5): Q9 left (D at top=466.2), Q10 left (D at top=713.9)
        9: {"page": 6, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 486.2}, "column": "left"},
        10: {"page": 6, "clipRectPt": {"x0": 20.0, "y0": 549.0, "x1": 271.4, "y1": 733.9}, "column": "left"},
        
        # Page 7 (index 6): Q11 left (D at top=391.4), Q12 left (D at top=603.1)
        11: {"page": 7, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 411.4}, "column": "left"},
        12: {"page": 7, "clipRectPt": {"x0": 20.0, "y0": 460.6, "x1": 271.4, "y1": 623.1}, "column": "left"},
        
        # Page 8 (index 7): Q13 full (D at top=274.8), Q14 full (D at top=690.6)
        13: {"page": 8, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 532.8, "y1": 294.8}, "column": "single"},
        14: {"page": 8, "clipRectPt": {"x0": 20.0, "y0": 439.6, "x1": 532.8, "y1": 710.6}, "column": "single"},
        
        # Page 9 (index 8): Q15 full (D at top=317.3), Q16 full (D at top=656.4)
        15: {"page": 9, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 532.8, "y1": 337.3}, "column": "single"},
        16: {"page": 9, "clipRectPt": {"x0": 20.0, "y0": 419.0, "x1": 532.8, "y1": 676.4}, "column": "single"},
        
        # Page 10 (index 9): Q17 left (D at top=310.0), Q18 left (D at top=682.6)
        17: {"page": 10, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 330.0}, "column": "left"},
        18: {"page": 10, "clipRectPt": {"x0": 20.0, "y0": 480.5, "x1": 271.4, "y1": 702.6}, "column": "left"},
        
        # Page 11 (index 10): Q19 left (D at top=383.1), Q20 right (D at top=393.3)
        19: {"page": 11, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 403.1}, "column": "left"},
        20: {"page": 11, "clipRectPt": {"x0": 281.4, "y0": 78.9, "x1": 532.8, "y1": 413.3}, "column": "right"},
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
    
    old_path = output_dir / f"MEB-LGS-2016-{subj.upper()}-Q{qnum:02d}.png"
    if old_path.exists():
        old_path.rename(output_dir / f"MEB-LGS-2016-{subj.upper()}-Q{qnum:02d}.png.bak")
    
    cropped.save(old_path, "PNG")
    asset_hash = sha256(old_path)
    h = clip['y1'] - clip['y0']
    print(f"  Fixed {subj} Q{qnum}: page={fix['page']} height={h:.1f}pt crop=({clip['x0']:.1f},{clip['y0']:.1f})-({clip['x1']:.1f},{clip['y1']:.1f})")
    return True


def update_manifest(subj: str, qnum: int, fix: dict):
    manifest_path = REPO / "lgs_18_26" / subj / "manifest_2016.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    for q in manifest["questions"]:
        if q["questionNumber"] == qnum:
            q["visual"]["clipRectPt"] = fix["clipRectPt"]
            q["page"] = fix["page"]
            break
    
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  Manifest updated: {subj} Q{qnum}")


def main():
    pdf_sayisal = INPUT_DIR / "2016 Sayısal.pdf"
    output_dir = REPO / "lgs_18_26" / "matematik"
    
    for qnum in range(1, 21):
        fix = FIXES["matematik"][qnum]
        re_crop_question(pdf_sayisal, "matematik", qnum, fix, output_dir)
        update_manifest("matematik", qnum, fix)
    
    # Copy to public/exams
    import shutil
    dst = REPO / "public" / "exams"
    for qnum in range(1, 21):
        src_png = output_dir / f"MEB-LGS-2016-MATEMATIK-Q{qnum:02d}.png"
        target = dst / f"2016-matematik-q{qnum:02d}.png"
        if src_png.exists():
            shutil.copy2(src_png, target)
            print(f"  Copied: {target.name}")
    
    print("Tamamlandı!")


if __name__ == "__main__":
    main()