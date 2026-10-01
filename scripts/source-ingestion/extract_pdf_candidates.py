#!/usr/bin/env python3
"""Extract conservative text candidates from a PDF; output is never VERIFIED."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from create_ingestion_manifest import validate_provenance

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

QUESTION_START = re.compile(r"^\s*(?:Soru\s*)?(\d{1,2})\s*[.)]\s*(.*)$", re.I)
OPTION = re.compile(r"(?:^|\n)\s*([A-D])\s*[).:]\s*(.+?)(?=\n\s*[A-D]\s*[).:]|$)", re.S)
ANSWER_PAIR = re.compile(r"(?<!\w)(\d{1,2})\s*[).:-]\s*([A-D])(?=\s|[,;|]|$)", re.I)


def extract_text(pdf_path):
    if PdfReader is None:
        raise RuntimeError("pypdf is required for PDF extraction; install it in the project environment")
    reader = PdfReader(str(pdf_path), strict=False)
    pages = []
    for number, page in enumerate(reader.pages, 1):
        try:
            pages.append({"page": number, "text": page.extract_text() or ""})
        except Exception as exc:
            pages.append({"page": number, "text": "", "error": type(exc).__name__})
    return pages


def segment_page(text, page):
    lines = text.splitlines()
    starts = []
    for index, line in enumerate(lines):
        match = QUESTION_START.match(line)
        if match:
            starts.append((index, int(match.group(1))))
    blocks = []
    for i, (start, number) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        option_matches = list(OPTION.finditer(body))
        options = {match.group(1).upper(): re.sub(r"\s+", " ", match.group(2)).strip() for match in option_matches}
        stem = body
        if option_matches:
            stem = body[:option_matches[0].start()].strip()
            stem = re.sub(r"^\s*(?:Soru\s*)?\d{1,2}\s*[).:]\s*", "", stem, flags=re.I)
        warnings = []
        if len(stem) < 20:
            warnings.append("short_or_incomplete_stem")
        if set(options) != {"A", "B", "C", "D"}:
            warnings.append("four_options_not_confidently_extracted")
        if len(body) < 45:
            warnings.append("low_text_density_or_scanned_content")
        blocks.append({"question_number": number, "page_start": page, "page_end": page, "stem": stem, "options": options, "extraction_warnings": warnings})
    return blocks


def extract(pdf_path, source, source_file_url, booklet, manifest=None):
    pages = extract_text(pdf_path)
    blocks = []
    for page in pages:
        blocks.extend(segment_page(page["text"], page["page"]))
    all_text = "\n".join(page["text"] for page in pages)
    answer_pairs = [{"question_number": int(number), "candidate": letter.upper()} for number, letter in ANSWER_PAIR.findall(all_text)]
    pdf_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    provenance = manifest or {}
    records = []
    for block in blocks:
        records.append({
            "schema_version": "1.0", "id": f"{source['id']}:{booklet}:Q{block['question_number']:02d}",
            "source": {"source_id": source["id"], "source_type": source["type"], "year": source.get("year"), "official_index_url": source["official_index_url"], "source_page_url": provenance.get("source_page_url"), "discovered_from": provenance.get("discovered_from"), "pdf_url": provenance.get("pdf_url", source_file_url), "final_url": provenance.get("final_url", source_file_url), "source_file_url": source_file_url, "redirect_chain": provenance.get("redirect_chain", [source_file_url]), "source_sha256": pdf_hash, "booklet": booklet, "question_number": block["question_number"]},
            "question": {"grade": 8, "subject": None, "stem": block["stem"], "options": block["options"], "page_start": block["page_start"], "page_end": block["page_end"]},
            "answer_key": {"candidate": next((row["candidate"] for row in answer_pairs if row["question_number"] == block["question_number"]), None), "answer": None, "authority": "OFFICIAL_MEB_ONLY", "source_verified": False, "answer_key_verified": False},
            "curriculum": {"LGS_REFERENCE_2018_PLUS": {"status": "UNMAPPED", "version": None, "subject": None, "unit": None, "topic": None, "learning_outcome": None, "skill": None, "evidence_url": None}, "CURRENT_TYMM": {"status": "UNMAPPED", "version": None, "subject": None, "unit": None, "topic": None, "learning_outcome": None, "skill": None, "evidence_url": None}},
            "extraction": {"method": "pypdf-text-v1", "retrieved_at": datetime.now(timezone.utc).isoformat(), "confidence": "LOW" if block["extraction_warnings"] else "UNREVIEWED", "warnings": block["extraction_warnings"], "answer_key_candidates": [row for row in answer_pairs if row["question_number"] == block["question_number"]]},
            "solution": None,
            "status": "NEEDS_REVIEW", "checks": {"source_verified": False, "year_verified": False, "booklet_verified": False, "question_number_verified": False, "text_verified": False, "options_verified": False, "answer_key_source_verified": False, "answer_key_verified": False, "curriculum_verified": False, "solution_verified": False, "duplicate_checked": False},
        })
    review_reasons = []
    if not any(page["text"].strip() for page in pages):
        review_reasons.append("no_extractable_text_or_scanned_pdf")
    if any(page.get("error") for page in pages):
        review_reasons.append("page_text_extraction_error")
    if not records:
        review_reasons.append("no_question_candidates_detected")
    if records and any(record["extraction"]["warnings"] for record in records):
        review_reasons.append("question_or_option_extraction_ambiguous")
    if not answer_pairs:
        review_reasons.append("no_answer_key_candidate_detected")
    return {
        "schema_version": "1.0", "source_id": source["id"], "source_sha256": pdf_hash,
        "pages": [{"page": row["page"], "text_characters": len(row["text"]), "extraction_error": row.get("error")} for row in pages],
        "candidate_count": len(records), "answer_key_candidate_count": len(answer_pairs), "records": records,
        "review_reasons": review_reasons, "status": "NEEDS_REVIEW", "published": False,
    }


def validate_manifest_for_pdf(manifest, source, pdf_path):
    source_file_url = manifest.get("source_file_url", "")
    pdf_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    if manifest.get("source_id") != source["id"] or manifest.get("sha256") != pdf_hash or manifest.get("status") != "NEEDS_REVIEW" or manifest.get("published") is not False:
        raise ValueError("manifest source id/hash/status does not match the archived PDF")
    if manifest.get("official_index_url") != source["official_index_url"]:
        raise ValueError("manifest index URL does not match the registered source")
    try:
        validate_provenance(source, manifest)
    except ValueError as exc:
        raise ValueError(f"manifest provenance is invalid: {exc}") from exc
    if manifest.get("source_file_url") != manifest.get("pdf_url"):
        raise ValueError("manifest source PDF URL does not match discovery record")
    if manifest.get("size_bytes") != pdf_path.stat().st_size:
        raise ValueError("manifest size does not match archived PDF")
    if manifest.get("content_type") != "application/pdf":
        raise ValueError("manifest Content-Type is not application/pdf")
    return source_file_url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--booklet", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    from download_official_pdfs import registered_source
    from validate_source_registry import official_host
    source = registered_source(args.source_id)
    if source.get("type") == "REAL_LGS" and (not isinstance(source.get("year"), int) or source["year"] < 2018):
        parser.error("pre-2018 REAL_LGS sources cannot enter canonical LGS staging")
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        source_file_url = validate_manifest_for_pdf(manifest, source, args.pdf)
        result = extract(args.pdf, source, source_file_url, args.booklet, manifest)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"candidates={result['candidate_count']} answer_key_candidates={result['answer_key_candidate_count']} review_reasons={','.join(result['review_reasons']) or 'none'} status=NEEDS_REVIEW published=false")

if __name__ == "__main__":
    main()
