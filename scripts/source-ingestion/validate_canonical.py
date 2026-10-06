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
OPTION_LETTERS = frozenset("ABCD")
REPRESENTATIONS = {"STRUCTURED_TEXT", "IMAGE_BACKED", "HYBRID"}
VISUAL_REQUIRED_FIELDS = ("authority", "asset_path", "public_path", "asset_sha256", "page", "clip_rect_pt", "render_dpi", "reconstructed_from_ocr")
# Görsel asset yalnızca repo-relative yol olarak taşınır: mutlak yol, ``..``
# dışına çıkış ve URL şeması reddedilir (path traversal / arbitrary file
# serving yüzeyi kapatılır). Her segment ayrı ayrı denetlenir; ``a/../b.png``
# ve ``..png`` gibi değerler de reddedilir.
PATH_SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
SAFE_ASSET_PATH = re.compile(r"^/?" + PATH_SEGMENT.pattern + r"(?:/" + PATH_SEGMENT.pattern + r")*\.png$")
SAFE_PUBLIC_PATH = re.compile(r"^/" + PATH_SEGMENT.pattern + r"(?:/" + PATH_SEGMENT.pattern + r")*\.png$")
SHA256_HEX = re.compile(r"^[a-f0-9]{64}$")


def safe_asset_path(value):
    """Görsel asset yolunun repo-relative ve traversal'sız olduğunu doğrular."""
    if not isinstance(value, str) or value.startswith("/") or "\\" in value:
        return False
    parts = value.split("/")
    return bool(SAFE_ASSET_PATH.fullmatch(value)) and all(part not in {".", ".."} for part in parts)


def safe_public_path(value):
    """Sunulacak görsel yolunun site-absolute, traversal'sız olduğunu doğrular."""
    if not isinstance(value, str) or not value.startswith("/") or value.startswith("//"):
        return False
    parts = value.split("/")[1:]
    return bool(SAFE_PUBLIC_PATH.fullmatch(value)) and all(part not in {".", ".."} for part in parts)


def representation_of(record):
    """Kaydın temsil modu. Alan yoksa ``STRUCTURED_TEXT`` (geriye uyumlu varsayılan)."""
    value = record.get("question", {}).get("representation")
    return value if value is not None else "STRUCTURED_TEXT"


def validate_visual(record):
    """Görsel varlığın kanıt zincirini doğrular; hata yoksa boş liste döner."""
    question = record.get("question", {})
    visual = question.get("visual")
    errors = []
    if visual is None:
        return errors
    if not isinstance(visual, dict):
        return ["visual must be an object or null"]
    for field in VISUAL_REQUIRED_FIELDS:
        if field not in visual:
            errors.append(f"visual is missing required provenance field: {field}")
    if visual.get("authority") != "ORIGINAL_MEB_PDF":
        errors.append("visual authority must be the original MEB PDF")
    if visual.get("reconstructed_from_ocr") is not False:
        errors.append("visual must not be reconstructed/redrawn from OCR")
    asset_path, public_path = visual.get("asset_path"), visual.get("public_path")
    if not safe_asset_path(asset_path):
        errors.append("visual asset_path must be a repo-relative .png path without traversal")
    if not safe_public_path(public_path):
        errors.append("visual public_path must be a lowercase site-absolute .png path")
    if not SHA256_HEX.fullmatch(str(visual.get("asset_sha256", ""))):
        errors.append("visual asset_sha256 must be lowercase SHA-256")
    page = visual.get("page")
    if not isinstance(page, int) or isinstance(page, bool) or page < 1:
        errors.append("visual page must be a positive integer")
    dpi = visual.get("render_dpi")
    if not isinstance(dpi, int) or isinstance(dpi, bool) or dpi < 150:
        errors.append("visual render_dpi must be an integer of at least 150")
    rect = visual.get("clip_rect_pt")
    if not isinstance(rect, dict) or set(rect) != {"x0", "y0", "x1", "y1"} or any(
        not isinstance(value, (int, float)) or isinstance(value, bool) for value in rect.values()
    ):
        errors.append("visual clip_rect_pt must carry numeric x0/y0/x1/y1 bounds")
    return errors


def validate_structure(question):
    """Yapısal kapı: eksik/boş seçenek ve temsil modu tutarlılığını ayrı ayrı raporlar.

    Option key var ama value boş ile A/B/C/D setinin eksik olması **farklı**
    hatalardır; ikisi de sessizce "geçerli soru" sayılmaz.
    """
    errors = []
    representation = question.get("representation")
    if representation is not None and representation not in REPRESENTATIONS:
        errors.append(f"unsupported question representation: {representation}")
    mode = representation or "STRUCTURED_TEXT"
    stem = question.get("stem")
    options = question.get("options")

    if stem is not None and not (isinstance(stem, str) and stem.strip()):
        errors.append("question stem is empty")
    if options is not None and not isinstance(options, dict):
        errors.append("question options must be an object or null")
        options = None

    if options is not None:
        missing = sorted(OPTION_LETTERS - set(options))
        if missing:
            errors.append(f"question options are missing A-D keys: {', '.join(missing)}")
        empty = sorted(key for key, value in options.items() if not isinstance(value, str) or not value.strip())
        if empty:
            errors.append(f"question options present but empty: {', '.join(empty)}")
        unexpected = sorted(set(options) - OPTION_LETTERS)
        if unexpected:
            errors.append(f"question options have keys outside A-D: {', '.join(unexpected)}")

    # Görsel ağırlıklı temsillerde yapılandırılmış içerik opsiyoneldir; ancak bu
    # seçenek kendiliğinden "geçerli soru" anlamına gelmez, görsel kanıt şarttır.
    if mode in {"STRUCTURED_TEXT", "HYBRID"}:
        if not (isinstance(stem, str) and stem.strip()):
            errors.append(f"{mode} representation requires a non-empty stem")
        if not isinstance(options, dict) or set(options) != OPTION_LETTERS or any(
            not isinstance(value, str) or not value.strip() for value in options.values()
        ):
            errors.append(f"{mode} representation requires exactly four non-empty A-D options")
    if mode in {"IMAGE_BACKED", "HYBRID"} and question.get("visual") is None:
        errors.append(f"{mode} representation requires a visual block with MEB PDF provenance")
    if mode == "IMAGE_BACKED" and isinstance(options, dict) and options and set(options) != OPTION_LETTERS:
        errors.append("IMAGE_BACKED record must not carry a partial A-D option set")
    return errors


def canonical_fingerprint(record):
    from build_review_queue import fingerprint
    question = record.get("question", {})
    visual = question.get("visual") or {}
    # Görsel-dominant kayıtta gövde/şıklar boş olabilir; temsil edilebilir metin
    # yoksa görsel kanıtın kendisi fingerprint girdisi olur. Aksi hâlde iki farklı
    # görsel soru "boş gövde + boş şık" olarak birbirinin kopyası görünür (R11).
    payload = {
        "stem": question.get("stem") or f"[visual:{visual.get('asset_sha256', '')}:{visual.get('page', '')}]",
        "options": question.get("options") or {},
    }
    return fingerprint(payload)


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
    # Yapısal kapı temsil moduna göre çalışır: STRUCTURED_TEXT/HYBRID tam
    # gövde+seçenek ister, IMAGE_BACKED görsel kanıtı ister. Eski koşulsuz
    # "dolu stem + tam A-D" kuralı, görsel soruları temsil edilemez hâle
    # getiriyordu (R9).
    errors.extend(validate_structure(question))
    errors.extend(validate_visual(record))
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
