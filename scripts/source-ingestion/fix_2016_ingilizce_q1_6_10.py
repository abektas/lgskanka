#!/usr/bin/env python3
"""Fix 2016 İngilizce Q1,6,7,8,9,10 - full width crops for right-column content."""
import json
import hashlib
from pathlib import Path
import fitz
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs_2016")
DPI = 300

# All English questions have content in RIGHT column or both columns
# Need FULL WIDTH crops (x0=20, x1=532.8)

FIXES = {
    "ingilizce": {
        # Q1: page 17, content in right col (top=520-570), options A-D at 570.4
        1: {"page": 17, "clipRectPt": {"x0": 20.0, "y0": 82.9, "x1": 532.8, "y1": 590.4}, "column": "single"},
        
        # Q6: page 19, options in right col at 662.5 (A=3, B=4, C=5, D=6)
        6: {"page": 19, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 532.8, "y1": 682.5}, "column": "single"},
        
        # Q7: page 19, starts at 428.2, content in right col at 642.0, options C,D at 662.5
        7: {"page": 19, "clipRectPt": {"x0": 20.0, "y0": 408.2, "x1": 532.8, "y1": 682.5}, "column": "single"},
        
        # Q8: page 20, dialogue in right col (top=208-462), options A-D at right col
        8: {"page": 20, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 532.8, "y1": 482.0}, "column": "single"},
        
        # Q9: page 20, starts at 462.0 left, content in right col, goes to page bottom
        9: {"page": 20, "clipRectPt": {"x0": 20.0, "y0": 442.0, "x1": 532.8, "y1": 709.5}, "column": "single"},
        
        # Q10: page 21, content in right col at 338.2, options A-D at right col
        10: {"page": 21, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 532.8, "y1": 709.5}, "column": "single"},
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
    print(f"  Fixed {subj} Q{qnum}: page={fix['page']} col={fix['column']} h={h:.1f}pt crop=({clip['x0']:.1f},{clip['y0']:.1f})-({clip['x1']:.1f},{clip['y1']:.1f})")
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
    pdf_sozel = INPUT_DIR / "2016 Sözel.pdf"
    output_dir = REPO / "lgs_18_26" / "ingilizce"
    
    for qnum in [1, 6, 7, 8, 9, 10]:
        fix = FIXES["ingilizce"][qnum]
        re_crop_question(pdf_sozel, "ingilizce", qnum, fix, output_dir)
        update_manifest("ingilizce", qnum, fix)
    
    import shutil
    dst = REPO / "public" / "exams"
    for qnum in [1, 6, 7, 8, 9, 10]:
        src_png = output_dir / f"MEB-LGS-2016-INGILIZCE-Q{qnum:02d}.png"
        target = dst / f"2016-ingilizce-q{qnum:02d}.png"
        if src_png.exists():
            shutil.copy2(src_png, target)
            print(f"  Copied: {target.name}")
    
    print("İngilizce Q1,6,7,8,9,10 tamamlandı!")


if __name__ == "__main__":
    main()