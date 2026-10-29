#!/usr/bin/env python3
"""Fix 2016 Fen Bilimleri Q5, Q6, Q7, Q8 crops from Sayısal PDF."""
import json
import hashlib
from pathlib import Path
import fitz
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs_2016")
DPI = 300

# Corrected bounds for 2016 Fen Bilimleri from Sayısal PDF
# Q5: page 14, left column, D at top=355.5 (left col)
# Q6: page 14, left column, D at top=685.6 (left col)  
# Q7: page 15, left column, D at top=355.2 (left col)
# Q8: page 15, right column, D at top=711.8 (right col)

FIXES = {
    "fen-bilimleri": {
        # Page 14: Q5 left, Q6 left (both single column page)
        5: {"page": 14, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 532.8, "y1": 375.5}, "column": "single"},
        6: {"page": 14, "clipRectPt": {"x0": 20.0, "y0": 375.5, "x1": 532.8, "y1": 705.6}, "column": "single"},
        # Page 15: Q7 left, Q8 right
        7: {"page": 15, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 375.2}, "column": "left"},
        8: {"page": 15, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 731.8}, "column": "right"},
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
    print(f"  Fixed {subj} Q{qnum}: page={fix['page']} col={fix['column']} h={h:.1f}pt")
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
    output_dir = REPO / "lgs_18_26" / "fen-bilimleri"
    
    for qnum in [5, 6, 7, 8]:
        fix = FIXES["fen-bilimleri"][qnum]
        re_crop_question(pdf_sayisal, "fen-bilimleri", qnum, fix, output_dir)
        update_manifest("fen-bilimleri", qnum, fix)
    
    import shutil
    dst = REPO / "public" / "exams"
    for qnum in [5, 6, 7, 8]:
        src_png = output_dir / f"MEB-LGS-2016-FENBİLİMLERİ-Q{qnum:02d}.png"
        target = dst / f"2016-fen-bilimleri-q{qnum:02d}.png"
        if src_png.exists():
            shutil.copy2(src_png, target)
            print(f"  Copied: {target.name}")
    
    print("Fen Bilimleri Q5-8 tamamlandı!")


if __name__ == "__main__":
    main()