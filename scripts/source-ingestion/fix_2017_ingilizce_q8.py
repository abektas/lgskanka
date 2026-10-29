#!/usr/bin/env python3
"""Fix 2017 İngilizce Q8 - crop includes options which are ABOVE the anchor."""
import json
import hashlib
from pathlib import Path
import fitz
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs_2017")
DPI = 300

# Q8: options at top=210-415, question text at anchor 486.3
# Current crop starts at 466.3 (below options) - WRONG
# Fix: start from top of options (210 - 20pt margin = 190) to page bottom

FIXES = {
    "ingilizce": {
        8: {"page": 20, "clipRectPt": {"x0": 20.0, "y0": 190.0, "x1": 532.8, "y1": 709.5}, "column": "single"},
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
    output_dir = REPO / "lgs_18_26" / "ingilizce"
    
    for qnum in [8]:
        fix = FIXES["ingilizce"][qnum]
        re_crop_question(pdf_sozel, "ingilizce", qnum, fix, output_dir)
        update_manifest("ingilizce", qnum, fix)
    
    import shutil
    dst = REPO / "public" / "exams"
    for qnum in [8]:
        src_png = output_dir / f"MEB-LGS-2017-INGILIZCE-Q{qnum:02d}.png"
        target = dst / f"2017-ingilizce-q{qnum:02d}.png"
        if src_png.exists():
            shutil.copy2(src_png, target)
            print(f"  Copied: {target.name}")
    
    print("İngilizce Q8 tamamlandı!")


if __name__ == "__main__":
    main()