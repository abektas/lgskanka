#!/usr/bin/env python3
"""Fix 2016 Türkçe Q6, Q10, Q15 crops."""
import json
import hashlib
from pathlib import Path
import fitz
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs_2016")
DPI = 300
MARGIN_PT = 20.0

FIXES = {
    "turkce": {
        # Q6: page 4, left column. Anchor at 494.6. D option likely on right col or below.
        # From page 4 analysis: D left at 338.8 (Q5), D right at 410.8 (Q7).
        # Q6 is left col at 494.6, so it spans to bottom of page or next page.
        # Next left anchor on page 5 is Q8 at 98.7 (new page), so Q6 goes to page bottom.
        # Actually D options for Q6 might be on right column or page 5.
        6: {"page": 4, "clipRectPt": {"x0": 20.0, "y0": 474.6, "x1": 532.8, "y1": 709.5}, "column": "left"},
        
        # Q10: page 6, single column. Anchor at 98.2. D at 544.2 (left col).
        # Crop from 78.2 to 564.2 (D+20pt)
        10: {"page": 6, "clipRectPt": {"x0": 20.0, "y0": 78.2, "x1": 532.8, "y1": 564.2}, "column": "single"},
        
        # Q15: page 8, left column. Anchor at 396.3. 
        # Left col D at 636.5 (probably Q14 or Q15).
        # Next left anchor is Q18 at 98.7 (page 9), so Q15 goes to D at 636.5 + 20pt = 656.5
        15: {"page": 8, "clipRectPt": {"x0": 20.0, "y0": 376.3, "x1": 271.4, "y1": 656.5}, "column": "left"},
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
    output_dir = REPO / "lgs_18_26" / "turkce"
    
    for qnum in [6, 10, 15]:
        fix = FIXES["turkce"][qnum]
        re_crop_question(pdf_sozel, "turkce", qnum, fix, output_dir)
        update_manifest("turkce", qnum, fix)
    
    import shutil
    dst = REPO / "public" / "exams"
    for qnum in [6, 10, 15]:
        src_png = output_dir / f"MEB-LGS-2016-TURKCE-Q{qnum:02d}.png"
        target = dst / f"2016-turkce-q{qnum:02d}.png"
        if src_png.exists():
            shutil.copy2(src_png, target)
            print(f"  Copied: {target.name}")
    
    print("Türkçe Q6, Q10, Q15 tamamlandı!")


if __name__ == "__main__":
    main()