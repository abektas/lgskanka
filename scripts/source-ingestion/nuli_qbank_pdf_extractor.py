#!/usr/bin/env python3
"""Nüli QBANK PDF -> question-image extractor.

This tool is deliberately a *source/asset extraction* layer, not a canonical
question authoring or verification layer. It never writes answer keys,
curriculum mappings, VERIFIED status, or canonical QBANK records.

Pipeline:
    official/source PDF
        -> page render (default 300 DPI)
        -> conservative question-number detection
        -> column grouping
        -> question-region crop
        -> PNG asset
        -> SHA-256
        -> extraction manifest

The PDF remains the authoritative source. Crop coordinates are stored in PDF
points; PNGs are derived artifacts. Ambiguous detections are retained in the
manifest with warnings instead of being silently "fixed".
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

try:
    import pdfplumber
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "pdfplumber is required. Install with: "
        "python -m pip install -r scripts/source-ingestion/requirements-pdf-extractor.txt"
    ) from exc


QUESTION_RE = re.compile(r"^(?P<number>\d{1,2})(?:[.)]|:)?$")
QUESTION_MIN = 1
QUESTION_MAX = 90
DEFAULT_DPI = 300
DEFAULT_MARGIN_PT = 4.0
DEFAULT_FOOTER_PT = 24.0
DEFAULT_HEADER_PT = 32.0


@dataclass(frozen=True)
class QuestionAnchor:
    number: int
    x0: float
    top: float
    x1: float
    bottom: float
    column: int
    confidence: float
    text: str


@dataclass(frozen=True)
class CropRecord:
    source_pdf: str
    source_sha256: str
    page: int
    question_number: int
    column: int
    crop_rect_pt: dict[str, float]
    render_dpi: int
    asset_path: str
    public_path: str
    asset_sha256: str
    width_px: int
    height_px: int
    detection_confidence: float
    warnings: list[str]
    text_preview: str


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalise_word_text(text: str) -> str:
    return text.strip().replace("\u00a0", " ")


def parse_question_number(text: str) -> int | None:
    match = QUESTION_RE.fullmatch(normalise_word_text(text))
    if not match:
        return None
    number = int(match.group("number"))
    if QUESTION_MIN <= number <= QUESTION_MAX:
        return number
    return None


def page_column_boundaries(page_width: float, words: list[dict]) -> list[tuple[float, float]]:
    """Infer one or two columns from word x positions without assuming a 50/50 split."""
    if not words:
        return [(0.0, page_width)]

    xs = sorted(float(w["x0"]) for w in words if "x0" in w)
    if len(xs) < 8:
        return [(0.0, page_width)]

    # A large empty horizontal gap is stronger evidence of two columns than a
    # hard-coded midpoint. Ignore tiny local gaps caused by normal word spacing.
    gaps = [(xs[i + 1] - xs[i], i) for i in range(len(xs) - 1)]
    gap, index = max(gaps, key=lambda item: item[0])
    if gap < page_width * 0.12:
        return [(0.0, page_width)]

    split = (xs[index] + xs[index + 1]) / 2
    if split < page_width * 0.30 or split > page_width * 0.70:
        return [(0.0, page_width)]
    return [(0.0, split), (split, page_width)]


def assign_column(x0: float, boundaries: list[tuple[float, float]]) -> int:
    for index, (left, right) in enumerate(boundaries):
        if left <= x0 < right or (index == len(boundaries) - 1 and x0 <= right):
            return index
    return len(boundaries) - 1


def detect_question_anchors(
    page,
    *,
    header_pt: float = DEFAULT_HEADER_PT,
    footer_pt: float = DEFAULT_FOOTER_PT,
) -> tuple[list[QuestionAnchor], list[str]]:
    """Find likely numbered question starts conservatively.

    This is intentionally not OCR and not semantic question parsing. It only
    identifies visible numeric anchors and records uncertainty. A human or a
    later visual-analysis stage remains authoritative for question boundaries.
    """
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
    boundaries = page_column_boundaries(float(page.width), words)
    candidates: list[QuestionAnchor] = []
    warnings: list[str] = []

    for word in words:
        number = parse_question_number(str(word.get("text", "")))
        if number is None:
            continue
        top = float(word.get("top", 0.0))
        bottom = float(word.get("bottom", top))
        x0 = float(word.get("x0", 0.0))
        x1 = float(word.get("x1", x0))

        if top < header_pt or bottom > float(page.height) - footer_pt:
            continue

        column = assign_column(x0, boundaries)
        # Stronger confidence for a number followed by a textual line nearby.
        nearby_text = [
            other
            for other in words
            if other is not word
            and abs(float(other.get("top", 0.0)) - top) < 18
            and float(other.get("x0", 0.0)) >= boundaries[column][0]
            and float(other.get("x0", 0.0)) <= boundaries[column][1]
        ]
        confidence = 0.85 if nearby_text else 0.60
        candidates.append(
            QuestionAnchor(
                number=number,
                x0=x0,
                top=top,
                x1=x1,
                bottom=bottom,
                column=column,
                confidence=confidence,
                text=normalise_word_text(str(word.get("text", ""))),
            )
        )

    # A page can contain the same number in headers/footers or diagrams.
    # Keep the strongest candidate for each (column, number, approximate row).
    candidates.sort(key=lambda item: (item.column, item.top, item.x0))
    deduped: list[QuestionAnchor] = []
    for candidate in candidates:
        duplicate = next(
            (
                existing
                for existing in reversed(deduped)
                if existing.column == candidate.column
                and existing.number == candidate.number
                and abs(existing.top - candidate.top) < 14
            ),
            None,
        )
        if duplicate is None:
            deduped.append(candidate)
        elif candidate.confidence > duplicate.confidence:
            deduped.remove(duplicate)
            deduped.append(candidate)

    if not deduped:
        warnings.append("No question-number anchors detected on this page")

    # A jump is not necessarily an error: a page may start/end mid-section.
    # We only flag suspicious local duplicates and large sequence ambiguity.
    by_column: dict[int, list[QuestionAnchor]] = {}
    for anchor in deduped:
        by_column.setdefault(anchor.column, []).append(anchor)
    for column, anchors in by_column.items():
        anchors.sort(key=lambda item: item.top)
        if len(anchors) >= 2:
            repeated = [a.number for a in anchors]
            if len(repeated) != len(set(repeated)):
                warnings.append(f"Column {column}: repeated question number candidates")

    return deduped, warnings


def group_anchors_by_column(anchors: Iterable[QuestionAnchor]) -> dict[int, list[QuestionAnchor]]:
    grouped: dict[int, list[QuestionAnchor]] = {}
    for anchor in anchors:
        grouped.setdefault(anchor.column, []).append(anchor)
    for values in grouped.values():
        values.sort(key=lambda item: item.top)
    return grouped


def make_crop_records(page, page_number: int, anchors: list[QuestionAnchor], boundaries, margin_pt: float) -> list[dict]:
    grouped = group_anchors_by_column(anchors)
    records: list[dict] = []

    for column, column_anchors in grouped.items():
        left, right = boundaries[column]
        for index, anchor in enumerate(column_anchors):
            next_top = (
                column_anchors[index + 1].top - margin_pt
                if index + 1 < len(column_anchors)
                else float(page.height) - DEFAULT_FOOTER_PT
            )
            top = max(0.0, anchor.top - margin_pt)
            bottom = min(float(page.height), max(anchor.bottom + margin_pt, next_top))
            if bottom <= top:
                continue
            records.append(
                {
                    "page": page_number,
                    "question_number": anchor.number,
                    "column": column,
                    "crop_rect_pt": {
                        "x0": round(left, 3),
                        "y0": round(top, 3),
                        "x1": round(right, 3),
                        "y1": round(bottom, 3),
                    },
                    "detection_confidence": anchor.confidence,
                    "warnings": [],
                }
            )
    return records


def crop_to_png(page, rect_pt: dict[str, float], dpi: int):
    image = page.to_image(resolution=dpi).original
    scale_x = image.width / float(page.width)
    scale_y = image.height / float(page.height)
    pixel_box = (
        max(0, math.floor(rect_pt["x0"] * scale_x)),
        max(0, math.floor(rect_pt["y0"] * scale_y)),
        min(image.width, math.ceil(rect_pt["x1"] * scale_x)),
        min(image.height, math.ceil(rect_pt["y1"] * scale_y)),
    )
    if pixel_box[2] <= pixel_box[0] or pixel_box[3] <= pixel_box[1]:
        raise ValueError(f"Invalid pixel crop derived from {rect_pt}")
    return image.crop(pixel_box)


def text_preview(page, rect_pt: dict[str, float], limit: int = 240) -> str:
    try:
        text = page.within_bbox(
            (
                rect_pt["x0"],
                rect_pt["y0"],
                rect_pt["x1"],
                rect_pt["y1"],
            )
        ).extract_text() or ""
    except Exception:
        return ""
    return " ".join(text.split())[:limit]


def safe_public_path(asset_path: str) -> str:
    return "/" + asset_path.replace("\\", "/")


def extract_pdf(
    pdf_path: Path,
    output_dir: Path,
    *,
    dpi: int = DEFAULT_DPI,
    page_start: int | None = None,
    page_end: int | None = None,
    margin_pt: float = DEFAULT_MARGIN_PT,
    overwrite: bool = False,
) -> dict:
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    if dpi < 150:
        raise ValueError("render DPI must be >= 150 for Nüli visual provenance")

    output_dir.mkdir(parents=True, exist_ok=True)
    source_sha = sha256_file(pdf_path)
    pages_manifest: list[dict] = []
    total_assets = 0

    with pdfplumber.open(pdf_path) as pdf:
        first = page_start or 1
        last = page_end or len(pdf.pages)
        if first < 1 or last > len(pdf.pages) or first > last:
            raise ValueError(f"Invalid page range: {first}-{last}; PDF has {len(pdf.pages)} pages")

        for page_number in range(first, last + 1):
            page = pdf.pages[page_number - 1]
            anchors, detection_warnings = detect_question_anchors(page)
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
            boundaries = page_column_boundaries(float(page.width), words)
            crop_specs = make_crop_records(page, page_number, anchors, boundaries, margin_pt)

            page_record = {
                "page": page_number,
                "width_pt": round(float(page.width), 3),
                "height_pt": round(float(page.height), 3),
                "columns": [
                    {"index": i, "x0": round(left, 3), "x1": round(right, 3)}
                    for i, (left, right) in enumerate(boundaries)
                ],
                "detected_anchors": [asdict(anchor) for anchor in anchors],
                "warnings": detection_warnings,
                "assets": [],
            }

            for spec in crop_specs:
                qn = spec["question_number"]
                filename = f"page-{page_number:03d}_q-{qn:02d}_c-{spec['column'] + 1}.png"
                asset_path = output_dir / filename
                if asset_path.exists() and not overwrite:
                    spec["warnings"].append("asset already exists; skipped (use --overwrite to replace)")
                    page_record["assets"].append(spec)
                    continue

                image = crop_to_png(page, spec["crop_rect_pt"], dpi)
                image.save(asset_path, "PNG")
                asset_sha = sha256_file(asset_path)
                preview = text_preview(page, spec["crop_rect_pt"])
                rel = asset_path.as_posix()
                spec.update(
                    {
                        "asset_path": rel,
                        "public_path": safe_public_path(rel),
                        "asset_sha256": asset_sha,
                        "width_px": image.width,
                        "height_px": image.height,
                        "render_dpi": dpi,
                        "text_preview": preview,
                    }
                )
                page_record["assets"].append(spec)
                total_assets += 1

            pages_manifest.append(page_record)

    manifest = {
        "manifest_version": "1.0",
        "tool": "nuli_qbank_pdf_extractor.py",
        "tool_contract": "source-extraction-only",
        "source": {
            "pdf_path": str(pdf_path),
            "source_sha256": source_sha,
        },
        "render": {
            "dpi": dpi,
            "coordinate_system": "PDF points",
            "crop_strategy": "question-number anchors + inferred columns",
        },
        "policy": {
            "writes_canonical_answer": False,
            "writes_curriculum_verification": False,
            "writes_verified_status": False,
            "ocr_reconstruction": False,
        },
        "pages": pages_manifest,
        "summary": {
            "pages_processed": len(pages_manifest),
            "assets_created": total_assets,
            "ambiguous_pages": sum(1 for page in pages_manifest if page["warnings"]),
        },
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Nüli QBANK deterministic PDF question cropper")
    parser.add_argument("pdf", type=Path, help="Authoritative MEB PDF")
    parser.add_argument("output_dir", type=Path, help="Directory for derived PNGs + manifest.json")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="Render DPI (default: 300; minimum: 150)")
    parser.add_argument("--page-start", type=int, default=None, help="1-based first page to process")
    parser.add_argument("--page-end", type=int, default=None, help="1-based last page to process")
    parser.add_argument("--margin-pt", type=float, default=DEFAULT_MARGIN_PT, help="Crop margin in PDF points")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing PNG assets")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = extract_pdf(
            args.pdf,
            args.output_dir,
            dpi=args.dpi,
            page_start=args.page_start,
            page_end=args.page_end,
            margin_pt=args.margin_pt,
            overwrite=args.overwrite,
        )
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    summary = manifest["summary"]
    print(
        "[OK] Nüli PDF extraction complete: "
        f"{summary['pages_processed']} pages, "
        f"{summary['assets_created']} new PNG assets, "
        f"{summary['ambiguous_pages']} pages with warnings"
    )
    print(f"[MANIFEST] {args.output_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
