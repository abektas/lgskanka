#!/usr/bin/env python3
"""Fix 2017 Türkçe Q7 and Q10 - include D options which are above current crop start."""
import json
import hashlib
from pathlib import Path
import fitz
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs_2017")
DPI = 300

# Q7: page 4, right column. D at top=326.8, content continues to 716.1 (beyond page)
# Q10: page 5, right column. D at top=375.5, content continues to 720.6

FIXES = {
    "turkce": {
        # Q7: start from D option (326.8) - 20pt = 306.8, end at page bottom
        7: {"page": 4, "clipRectPt": {"x0": 281.4, "y0": 306.8, "x1": 532.8, "y1": 709.5}, "column": "right"},
        # Q10: start from D option (375.5) - 20pt = 355.5, end at page bottom  
        10: {"page": 5, "clipRectPt": {"x0": 281.4, "y0": 355.5, "x1": 532.8, "y1": 709.5}, "column": "right"},
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
        old_path.rename(output_dir / f"MEB-LGS-2017-{subj.upper()}-Q{qnum:02d}.png.bak")
    
    cropped.save(old_path, "PNG")
    asset_hash = sha256(old_path)
    h = clip['y1'] - clip['y0']
    print(f"  Fixed {subj} Q{qnum}: page={fix['page']} col={fix['column']} h={h:.1f}pt crop=({clip['x0']:.1f},{clip['y0']:.1f})-({clip['x1']:.1f},{clip['y1']:.1f})")
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
    pdf_sozel = INPUT_DIR / "2017 Sözel.pdf"
    output_dir = REPO / "lgs_18_26" / "turkce"
    
    for qnum in [7, 10]:
        fix = FIXES["turkce"][qnum]
        re_crop_question(pdf_sozel, "turkce", qnum, fix, output_dir)
        update_manifest("turkce", qnum, fix)
    
    import shutil
    dst = REPO / "public" / "exams"
    for qnum in [7, 10]:
        src_png = output_dir / f"MEB-LGS-2017-TURKCE-Q{qnum:02d}.png"
        target = dst / f"2017-turkce-q{qnum:02d}.png"
        if src_png.exists():
            shutil.copy2(src_png, target)
            print(f"  Copied: {target.name}")
    
    print("Türkçe Q7, Q10 tamamlandı!")


if __name__ == "__main__":
    main()