#!/usr/bin/env python3
"""Fix fen-bilimleri 2017 Q14 and Q16 crops from correct PDF (Sayısal)."""
import json
import hashlib
from pathlib import Path
import fitz
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs_2017")
DPI = 300

# Corrected bounds for Fen Bilimleri from Sayısal PDF
FIXES = {
    "fen-bilimleri": {
        14: {
            "page": 15,  # 1-indexed
            "clipRectPt": {"x0": 20.0, "y0": 408.9, "x1": 532.8, "y1": 709.5},
            "column": "single"
        },
        16: {
            "page": 16,  # 1-indexed
            "clipRectPt": {"x0": 20.0, "y0": 393.3, "x1": 532.8, "y1": 709.5},
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
    """Re-crop a single question with corrected bounds."""
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
    
    # Backup old file
    old_path = output_dir / f"MEB-LGS-2017-{subj.upper()}-Q{qnum:02d}.png"
    if old_path.exists():
        old_path.rename(output_dir / f"MEB-LGS-2017-{subj.upper()}-Q{qnum:02d}.png.bak2")
    
    cropped.save(old_path, "PNG")
    asset_hash = sha256(old_path)
    print(f"  Fixed {subj} Q{qnum}: page={fix['page']} crop=({clip['x0']:.1f},{clip['y0']:.1f})-({clip['x1']:.1f},{clip['y1']:.1f}) hash={asset_hash[:16]}...")
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
    pdf_sayisal = INPUT_DIR / "2017 Sayısal.pdf"
    output_dir = REPO / "lgs_18_26" / "fen-bilimleri"
    
    for qnum, fix in FIXES["fen-bilimleri"].items():
        re_crop_question(pdf_sayisal, "fen-bilimleri", qnum, fix, output_dir)
        update_manifest("fen-bilimleri", qnum, fix)
    
    print("\nKopyalama public/exams'e...")
    import shutil, re
    base = REPO
    src = base / "lgs_18_26" / "fen-bilimleri"
    dst = base / "public" / "exams"
    for png in src.glob('MEB-LGS-2017-FENBİLİMLERİ-Q14.png'):
        m = re.search(r'Q(\d+)', png.name)
        if m:
            qnum = int(m.group(1))
            target = dst / f'2017-fen-bilimleri-q{str(qnum).zfill(2)}.png'
            shutil.copy2(png, target)
            print(f"  Copied: {target.name}")
    for png in src.glob('MEB-LGS-2017-FENBİLİMLERİ-Q16.png'):
        m = re.search(r'Q(\d+)', png.name)
        if m:
            qnum = int(m.group(1))
            target = dst / f'2017-fen-bilimleri-q{str(qnum).zfill(2)}.png'
            shutil.copy2(png, target)
            print(f"  Copied: {target.name}")
    
    print("Tamamlandı!")


if __name__ == "__main__":
    main()