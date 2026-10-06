#!/usr/bin/env python3
"""2022 görsel soru pilotu için resmî MEB sayfasından soru bölgesini kırpar.

TASK-QBANK-003. Amaç: pypdf'in düz metin olarak temsil edemediği soruların
(şekil/tablo/grafik/denklem) orijinal görselini, resmî PDF'den yeniden
*çizmeden* koruyan bir pilot üretmek.

Tasarım kararları:
  * Kaynak PDF değişmez (immutable). Kırpma yalnızca okuma ile yapılır.
  * Bölge bulma PyMuPDF metin bloklarına dayanır: sol marjda `N.` ile başlayan
    blok sorunun başlangıcı, bir sonraki böyle bloğun üstü (yoksa içerik
    tabanı) bölgenin sonudur.
  * Metin OCR ile yeniden kurulmaz; PNG resmî sayfanın birebir raster
    gösterimidir. Bu yüzden cevap anahtarı bilinçli olarak çıktıya yazılmaz.
  * Çıktı `NEEDS_REVIEW` / `published=false` durumundadır.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pymupdf

QUESTION_START = re.compile(r"^\s*(\d{1,2})\.\s")
START_COLUMN_MAX_X = 80.0          # sol marj sütunu
CONTENT_BOTTOM_Y = 735.0           # "Diğer sayfaya geçiniz." altındaki taban
PAD_PT = 6.0
RENDER_DPI = 300


def question_anchors(page: pymupdf.Page) -> list[tuple[float, int]]:
    """Sayfadaki soru numarası bloklarını (y, numara) olarak döndürür."""
    anchors = []
    for block in page.get_text("blocks"):
        x0, y0, text = block[0], block[1], block[4]
        match = QUESTION_START.match(text)
        if x0 <= START_COLUMN_MAX_X and match:
            anchors.append((y0, int(match.group(1))))
    return sorted(anchors)


def region_for(page: pymupdf.Page, question_number: int) -> pymupdf.Rect:
    """Verilen soru numarasının sayfa üzerindeki dikdörtgen bölgesini bulur."""
    anchors = question_anchors(page)
    start = next((y for y, n in anchors if n == question_number), None)
    if start is None:
        raise ValueError(f"sayfa {page.number + 1} üzerinde soru {question_number} bulunamadı")
    later = [y for y, _n in anchors if y > start + 1.0]
    end = min(min(later), CONTENT_BOTTOM_Y) if later else CONTENT_BOTTOM_Y

    top = max(0.0, start - PAD_PT)
    bottom = max(top + 10.0, end - PAD_PT)
    blocks = [
        b for b in page.get_text("blocks")
        if b[1] >= top - 1.0 and b[3] <= bottom + 1.0
    ]
    left = min((b[0] for b in blocks), default=page.rect.x0 + 30)
    right = max((b[2] for b in blocks), default=page.rect.x1 - 30)
    return (pymupdf.Rect(left - PAD_PT, top, right + PAD_PT, bottom) & page.rect)
def load_mineru_pages(paths: list[Path]) -> dict[int, dict[str, Any]]:
    """MinerU (flash tier) JSON çıktısını sayfa indeksine göre düzleştirir.

    MinerU çıktısı karşılaştırma amaçlıdır; resmî kaynak değildir.
    """
    pages: dict[int, dict[str, Any]] = {}
    for path in paths:
        doc = json.loads(path.read_text(encoding="utf-8"))
        for page in doc.get("pages", []):
            types: dict[str, int] = {}
            texts: list[str] = []
            for block in page.get("blocks", []):
                types[block.get("type", "?")] = types.get(block.get("type", "?"), 0) + 1
                for item in block.get("content", []):
                    if item.get("type") == "text" and item.get("content"):
                        texts.append(str(item["content"]))
            pages[int(page["page_idx"]) + 1] = {
                "block_types": types,
                "text_excerpt": " | ".join(texts)[:1200],
            }
    return pages


def render(
    pdf_path: Path,
    targets: list[dict],
    image_dir: Path,
    source: dict,
    staging_records: dict[tuple[str, int], dict],
    mineru_pages: dict[int, dict[str, Any]],
) -> dict:
    image_dir.mkdir(parents=True, exist_ok=True)
    zoom = RENDER_DPI / 72.0
    matrix = pymupdf.Matrix(zoom, zoom)
    cwd = Path.cwd()
    records = []
    with pymupdf.open(pdf_path) as doc:
        for target in targets:
            page = doc[target["page"] - 1]
            rect = region_for(page, target["question_number"])
            pixmap = page.get_pixmap(matrix=matrix, clip=rect, alpha=False)
            filename = (
                f"{target['subject_code'].lower()}-q{target['question_number']:02d}"
                f"-p{target['page']:02d}.png"
            )
            path = image_dir / filename
            pixmap.save(path)
            mode = target.get("mode", "image")
            key = (target["subject"], target["question_number"])
            staging_record = staging_records.get(key)
            mineru_page = mineru_pages.get(target["page"])
            records.append({
                "id": f"{source['source_id']}:SAYISAL:{target['subject_code']}:Q{target['question_number']:02d}",
                "mode": mode,
                "source": {
                    "source_id": source["source_id"],
                    "source_type": source["source_type"],
                    "year": source["year"],
                    "booklet": "SAYISAL",
                    "source_page_url": source["source_page_url"],
                    "pdf_url": source["pdf_url"],
                    "source_sha256": source["sha256"],
                    "archive_path": str(pdf_path),
                },
                "question": {
                    "subject": target["subject"],
                    "subject_code": target["subject_code"],
                    "question_number": target["question_number"],
                    "page": target["page"],
                    "representation": (
                        "IMAGE_BACKED" if mode == "image" else "STRUCTURED_TEXT"
                    ),
                },
                "image": {
                    "path": path.relative_to(cwd).as_posix() if path.is_relative_to(cwd) else path.as_posix(),
                    "public_path": f"/pilot-2022-visual/{filename}",
                    "pixel_width": pixmap.width,
                    "pixel_height": pixmap.height,
                    "clip_rect_pt": {
                        "x0": round(rect.x0, 2), "y0": round(rect.y0, 2),
                        "x1": round(rect.x1, 2), "y1": round(rect.y1, 2),
                    },
                },
                "extraction": {
                    "tool": "PyMuPDF",
                    "tool_version": pymupdf.version[0],
                    "method": "page_render_clip",
                    "render_dpi": RENDER_DPI,
                    "region_detection": "left_margin_question_number_blocks",
                    "page_embedded_images": len(page.get_images(full=True)),
                    "page_vector_drawings": len(page.get_drawings()),
                    "page_text_characters": len(page.get_text("text")),
                    "reconstructed_from_ocr": False,
                },
                "reason": target["reason"],
                "baseline": {
                    "baseline_tool": "pypdf",
                    "produced_question_block": bool(staging_record),
                    "page_text_excerpt": target.get("debug_excerpt", ""),
                    "authoritative": False,
                },
                "structured_text": (
                    {
                        "tool": "pypdf",
                        "authoritative": False,
                        "stem": staging_record["question"]["stem"],
                        "options": staging_record["question"]["options"],
                    }
                    if staging_record
                    else None
                ),
                "mineru_comparison": (
                    {
                        "tool": "MinerU",
                        "tier": "flash",
                        "authoritative": False,
                        "note": (
                            "Yerel MinerU yalnızca flash (parse_mode=txt) tier ile "
                            "çalıştı; layout/table modelleri bu ortamda yok. "
                            "Metin bloğu çıkarımı karşılaştırma amaçlıdır."
                        ),
                        **mineru_page,
                    }
                    if mineru_page
                    else None
                ),
                # Cevap anahtarı bilinçli olarak dahil edilmez.
                "status": "NEEDS_REVIEW",
                "published": False,
            })
    return {
        "schema_version": "1.0",
        "pilot": "TASK-QBANK-003-2022-visual-representation",
        "source": source,
        "tooling": {
            "render_tool": "PyMuPDF",
            "render_tool_version": pymupdf.version[0],
            "render_dpi": RENDER_DPI,
            "baseline_tool": "pypdf",
            "layout_tool": "MinerU (flash tier, karşılaştırma amaçlı)",
        },
        "candidate_count": len(records),
        "image_backed_count": sum(1 for r in records if r["mode"] == "image"),
        "control_count": sum(1 for r in records if r["mode"] == "control"),
        "records": records,
        "status": "NEEDS_REVIEW",
        "published": False,
    }


def load_staging(path: Path) -> dict[tuple[str, int], dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {
        (r["question"]["subject"], r["source"]["question_number"]): r
        for r in doc["records"]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True, help="JSON hedef listesi")
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--staging",
        type=Path,
        default=Path(__file__).parent / "data/questions/staging/MEB-LGS-2022__SAYISAL.json",
        help="pypdf metin tabanı (structured_text karşılaştırması için)",
    )
    parser.add_argument(
        "--mineru-json",
        type=Path,
        nargs="*",
        default=[],
        help="MinerU parse JSON dosyaları (karşılaştırma amaçlı)",
    )
    args = parser.parse_args()

    pdf_path = args.pdf
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    targets_doc = json.loads(args.targets.read_text(encoding="utf-8"))
    source = dict(targets_doc["source"])
    expected = source.pop("expected_sha256")
    if digest != expected:
        raise SystemExit(f"SHA-256 uyuşmuyor: {digest} != {expected}")
    source["sha256"] = digest

    staging = load_staging(args.staging) if args.staging.exists() else {}
    mineru_pages = load_mineru_pages(args.mineru_json)

    result = render(
        pdf_path,
        targets_doc["targets"],
        args.image_dir,
        source,
        staging,
        mineru_pages,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"pilot={result['pilot']} records={result['candidate_count']} "
        f"sha256={digest} status=NEEDS_REVIEW published=false"
    )
    for row in result["records"]:
        print(
            f"  {row['question']['subject']} Q{row['question']['question_number']:02d} "
            f"page={row['question']['page']} mode={row['mode']} -> {row['image']['path']} "
            f"({row['image']['pixel_width']}x{row['image']['pixel_height']})"
        )


if __name__ == "__main__":
    main()