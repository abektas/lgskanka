#!/usr/bin/env python3
"""Deterministic validation and lifecycle gate for canonical staging records."""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from source_trust import is_allowed_pdf_host, validate_pdf_redirect
from validate_source_registry import official_host

REQUIRED_CHECKS = ("source_verified", "year_verified", "booklet_verified", "question_number_verified", "text_verified", "options_verified", "answer_key_source_verified", "answer_key_verified", "curriculum_verified", "solution_verified", "duplicate_checked")
ALLOWED_STATUSES = {"DRAFT", "EXTRACTED", "AUTO_CHECKED", "NEEDS_REVIEW", "VERIFIED", "REJECTED"}


def canonical_fingerprint(record):
    from build_review_queue import fingerprint
    question = record.get("question", {})
    return fingerprint({"stem": question.get("stem"), "options": question.get("options")})


def validate_record(record, require_verified=False):
    require_verified = require_verified or record.get("status") == "VERIFIED"
    errors = []
    if record.get("schema_version") != "1.0": errors.append("unsupported schema_version")
    if record.get("status") not in ALLOWED_STATUSES: errors.append("invalid lifecycle status")
    source = record.get("source", {})
    kind, year = source.get("source_type"), source.get("year")
    if kind == "REAL_LGS" and (not isinstance(year, int) or year < 2018): errors.append("REAL_LGS year must be 2018 or later")
    if kind not in {"REAL_LGS", "MEB_SAMPLE"}: errors.append("unsupported official source type")
    if not str(source.get("source_id", "")).startswith("MEB-"): errors.append("official source identity must start MEB-")
    for field in ("official_index_url", "source_page_url", "discovered_from"):
        url = source.get(field, "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or not official_host(parsed.hostname.lower()): errors.append(f"{field} must use official MEB HTTPS host")
    for field in ("pdf_url", "final_url", "source_file_url"):
        url = source.get(field, "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or not is_allowed_pdf_host(parsed.hostname.lower()): errors.append(f"{field} must use official MEB/CDN PDF URL")
    if source.get("source_file_url") != source.get("pdf_url"):
        errors.append("source_file_url must match discovered PDF URL")
    chain = source.get("redirect_chain")
    if not isinstance(chain, list) or not chain or chain[0] != source.get("pdf_url") or chain[-1] != source.get("final_url"):
        errors.append("PDF redirect chain is incomplete")
    elif not errors:
        for previous, current in zip(chain, chain[1:]):
            try:
                validate_pdf_redirect(previous, current)
            except ValueError as exc:
                errors.append(str(exc))
    if not re.fullmatch(r"[a-f0-9]{64}", source.get("source_sha256", "")): errors.append("source_sha256 must be lowercase SHA-256")
    question = record.get("question", {})
    if question.get("grade") != 8: errors.append("grade must be 8")
    if require_verified and (not isinstance(record.get("solution"), str) or not record["solution"].strip()): errors.append("verified record requires a reviewed solution")
    if require_verified and not str(source.get("booklet", "")).strip(): errors.append("verified record requires a booklet identity")
    if require_verified and (not isinstance(source.get("question_number"), int) or isinstance(source.get("question_number"), bool) or source["question_number"] < 1): errors.append("verified record requires a positive question number")
    if not isinstance(question.get("stem"), str) or not question["stem"].strip(): errors.append("question stem is empty")
    options = question.get("options")
    if not isinstance(options, dict) or set(options) != {"A", "B", "C", "D"} or any(not isinstance(v, str) or not v.strip() for v in options.values()): errors.append("exactly four non-empty A-D options are required")
    answer = record.get("answer_key", {})
    if answer.get("authority") != "OFFICIAL_MEB_ONLY": errors.append("answer authority must be official MEB")
    if answer.get("answer") is not None and answer.get("answer") not in {"A", "B", "C", "D"}: errors.append("canonical answer must be an A-D official answer key value")
    if require_verified and answer.get("answer") not in {"A", "B", "C", "D"}: errors.append("canonical answer must be an A-D official answer key value")
    if require_verified and answer.get("source_verified") is not True: errors.append("answer-key source is not independently verified")
    if require_verified and answer.get("answer_key_verified") is not True: errors.append("answer key is not independently verified")
    curriculum = record.get("curriculum", {})
    if set(curriculum) != {"LGS_REFERENCE_2018_PLUS", "CURRENT_TYMM"}: errors.append("both curriculum layers must be represented")
    if require_verified and not any(isinstance(m, dict) and m.get("status") == "VERIFIED" and all(isinstance(m.get(k), str) and m[k].strip() for k in ("version", "subject", "unit", "topic", "learning_outcome", "skill", "evidence_url")) for m in curriculum.values()): errors.append("at least one evidence-backed curriculum mapping must be VERIFIED")
    checks = record.get("checks", {})
    if require_verified:
        for key in REQUIRED_CHECKS:
            if checks.get(key) is not True: errors.append(f"required check is false or missing: {key}")
    if not canonical_fingerprint(record): errors.append("cannot compute duplicate fingerprint")
    return errors


def transition(record, target):
    current = record.get("status")
    if target not in ALLOWED_STATUSES:
        raise ValueError(f"invalid target status: {target}")
    if target == "VERIFIED":
        if current != "NEEDS_REVIEW": raise ValueError("only NEEDS_REVIEW records can transition to VERIFIED")
        errors = validate_record(record, require_verified=True)
        if errors: raise ValueError("verification gate failed: " + "; ".join(errors))
    elif current == "VERIFIED" and target != "REJECTED":
        raise ValueError("VERIFIED is terminal except for explicit rejection")
    elif current == "NEEDS_REVIEW" and target not in {"NEEDS_REVIEW", "VERIFIED", "REJECTED"}:
        raise ValueError("invalid NEEDS_REVIEW transition")
    result = dict(record)
    result["status"] = target
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("records", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.records.read_text(encoding="utf-8"))
    records = payload if isinstance(payload, list) else payload.get("records", [])
    issues = [(row.get("id", "<missing>"), validate_record(row)) for row in records]
    issues = [(record_id, errors) for record_id, errors in issues if errors]
    if issues:
        for record_id, errors in issues:
            for error in errors: print(f"{record_id}: {error}", file=sys.stderr)
        raise SystemExit(1)
    print(f"OK: {len(records)} structurally valid canonical record(s); lifecycle statuses unchanged")

if __name__ == "__main__": main()
