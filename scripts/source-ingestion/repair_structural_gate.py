#!/usr/bin/env python3
"""Yapısal kapıdan geçemeyen metin adaylarını görsel-dominant kayda dönüştürür.

TASK-QBANK-005 · R10. 2022 Sayısal staging'indeki iki kayıt (`FEN:Q15` boş
option value, `FEN:Q18` eksik option set) pypdf metniyle temsil edilemiyor.
Bu betik:

  * seçenek/gövde metnini **uydurmaz** — hiçbir seçenek veya cevap üretmez,
  * resmî PDF'in kendi sayfasından PyMuPDF ile kırpma alır (yeniden çizim/OCR yok),
  * kırpmanın SHA-256'sını, sayfa/bbox/DPI bilgisini `question.visual` içine yazar,
  * kaydı `representation: "IMAGE_BACKED"` olarak işaretler,
  * `NEEDS_REVIEW` / `published=false` sınırını ve `answer: null` durumunu korur.

Çıktı yalnızca staging'dir; hiçbir kayıt `VERIFIED` olmaz ve cevap anahtarı
üretilmez. Dönüşüm **yalnızca** metinle temsil edilemeyen, görsel kanıtı
bulunabilen kayıtlara uygulanır; temsil edilebilir kayıtlar hiç değişmez.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import pymupdf

from render_visual_pilot import region_for, RENDER_DPI


def render_crop(pdf_path: Path, page_number: int, question_number: int, image_dir: Path) -> dict:
    """Resmî sayfadan soru bölgesini kırpır ve kanıt kimliğini döndürür."""
    image_dir.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(pdf_path) as doc:
        page = doc[page_number - 1]
        rect = region_for(page, question_number)
        matrix = pymupdf.Matrix(RENDER_DPI / 72.0, RENDER_DPI / 72.0)
        pixmap = page.get_pixmap(matrix=matrix, clip=rect, alpha=False)
    filename = f"img-q{question_number:02d}-p{page_number:02d}.png"
    path = image_dir / filename
    pixmap.save(path)
    return {
        "authority": "ORIGINAL_MEB_PDF",
        "asset_path": path.as_posix(),
        "public_path": f"/pilot-2022-visual/{filename}",
        "asset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "page": page_number,
        "clip_rect_pt": {
            "x0": round(rect.x0, 2), "y0": round(rect.y0, 2),
            "x1": round(rect.x1, 2), "y1": round(rect.y1, 2),
        },
        "render_dpi": RENDER_DPI,
        "reconstructed_from_ocr": False,
    }


def needs_visual_representation(record: dict) -> bool:
    """Yalnızca metinle temsil edilemeyen kayıtlar dönüştürülür.

    Gövde ya da A-D seti eksik/boşsa pypdf bu soruyu bozdu demektir; bu
    durumda görsel kanıt zorunlu kılınır. Tam temsil edilebilen kayıtlara
    dokunulmaz (regresyon yok).
    """
    question = record.get("question", {})
    options = question.get("options")
    stem_ok = isinstance(question.get("stem"), str) and bool(question["stem"].strip())
    options_ok = (
        isinstance(options, dict)
        and set(options) == {"A", "B", "C", "D"}
        and all(isinstance(value, str) and value.strip() for value in options.values())
    )
    return not (stem_ok and options_ok)
def repair(payload: dict, pdf_path: Path, image_dir: Path) -> tuple[dict, list[str]]:
    records = payload.get("records", [])
    repaired, changed = [], []
    for record in records:
        if not needs_visual_representation(record):
            repaired.append(record)
            continue
        page_number = record["question"]["page_start"]
        question_number = record["source"]["question_number"]
        # pypdf çıktısı resmî metin DEĞİLDİR ve bu kayıtta bozuktur; bu
        # yüzden stem/options tutulmaz, yalnızca görsel kanıt esas alınır.
        new_record = copy.deepcopy(record)
        new_record["question"].update(
            {
                "stem": None,
                "options": None,
                "representation": "IMAGE_BACKED",
                "visual": render_crop(pdf_path, page_number, question_number, image_dir),
            }
        )
        extraction = new_record.setdefault("extraction", {})
        warnings = list(extraction.get("warnings", []))
        for warning in ("structured_text_not_representable", "visual_crop_required"):
            if warning not in warnings:
                warnings.append(warning)
        extraction["warnings"] = warnings
        extraction["confidence"] = "LOW"
        # Yaşam döngüsü sınırı: dönüşüm asla doğrulama veya yayınlama yapmaz.
        new_record["status"] = "NEEDS_REVIEW"
        new_record["answer_key"]["answer"] = None
        new_record["solution"] = None
        repaired.append(new_record)
        changed.append(record["id"])
    result = dict(payload)
    result["records"] = repaired
    result["visual_backed_record_count"] = sum(
        1 for record in repaired
        if record.get("question", {}).get("representation") == "IMAGE_BACKED"
    )
    result["status"] = "NEEDS_REVIEW"
    result["published"] = False
    return result, changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, required=True, help="resmî arşiv PDF'i (SHA-256 doğrulanır)")
    parser.add_argument("--expected-sha256", required=True, help="PDF'in beklenen SHA-256'sı")
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    digest = hashlib.sha256(args.pdf.read_bytes()).hexdigest()
    if digest != args.expected_sha256:
        raise SystemExit(f"PDF SHA-256 uyuşmuyor: {digest} != {args.expected_sha256}")

    payload = json.loads(args.staging.read_text(encoding="utf-8"))
    staging_sha = payload.get("source_sha256")
    if staging_sha and staging_sha != digest:
        raise SystemExit(f"staging source_sha256 PDF ile eşleşmiyor: {staging_sha} != {digest}")

    result, changed = repair(payload, args.pdf, args.image_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"visual_backed={result['visual_backed_record_count']} "
        f"changed={','.join(changed) or 'none'} status=NEEDS_REVIEW published=false"
    )


if __name__ == "__main__":
    main()