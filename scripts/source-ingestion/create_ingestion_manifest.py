#!/usr/bin/env python3
"""Hash a local PDF and emit a non-publishing, review-required ingestion manifest."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from source_trust import is_allowed_pdf_host, validate_pdf_redirect
from validate_source_registry import REGISTRY, official_host


def _legacy_provenance(source: dict, url: str) -> dict:
    parsed = urlparse(url)
    if url != source.get("official_index_url"):
        raise ValueError("URL must exactly match the registered official index URL")
    if parsed.scheme != "https" or not parsed.hostname or not official_host(parsed.hostname.lower()):
        raise ValueError("URL host is outside the official MEB allowlist")
    return {
        "source_page_url": url,
        "discovered_from": url,
        "pdf_url": url,
        "final_url": url,
        "content_type": "application/pdf",
        "redirect_chain": [url],
        "discovery_redirect_chain": [url],
    }


def validate_provenance(source: dict, provenance: dict) -> dict:
    if not isinstance(provenance, dict):
        raise ValueError("manifest provenance must be an object")
    required = ("source_page_url", "discovered_from", "pdf_url", "final_url", "content_type", "redirect_chain")
    if any(not provenance.get(field) for field in required):
        raise ValueError("manifest provenance is incomplete")
    for field in ("source_page_url", "discovered_from"):
        parsed = urlparse(provenance[field])
        if parsed.scheme != "https" or not parsed.hostname or not official_host(parsed.hostname.lower()):
            raise ValueError(f"{field} must be an official MEB HTTPS page")
    for field in ("pdf_url", "final_url"):
        parsed = urlparse(provenance[field])
        if parsed.scheme != "https" or not parsed.hostname or not is_allowed_pdf_host(parsed.hostname.lower()):
            raise ValueError(f"{field} is outside the official MEB/CDN PDF target policy")
    chain = provenance["redirect_chain"]
    if not isinstance(chain, list) or not chain or chain[0] != provenance["pdf_url"] or chain[-1] != provenance["final_url"]:
        raise ValueError("PDF redirect chain is incomplete")
    for previous, current in zip(chain, chain[1:]):
        validate_pdf_redirect(previous, current)
    if not isinstance(provenance.get("discovery_redirect_chain", [provenance["source_page_url"]]), list):
        raise ValueError("official-page redirect chain must be an array")
    return provenance


def create_manifest(pdf: Path, source: dict, provenance: dict | str) -> dict:
    if isinstance(provenance, str):
        provenance = _legacy_provenance(source, provenance)
    provenance = validate_provenance(source, provenance)
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        raise ValueError("input must be an existing PDF file")
    size = pdf.stat().st_size
    if size > 100 * 1024 * 1024:
        raise ValueError("PDF exceeds the 100 MiB ingestion safety limit")
    with pdf.open("rb") as source_file:
        signature = source_file.read(5)
        if signature != b"%PDF-":
            raise ValueError("input does not have a PDF signature")
        source_file.seek(0)
        digest = hashlib.sha256()
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    digest = digest.hexdigest()
    if provenance.get("sha256") and provenance["sha256"] != digest:
        raise ValueError("download SHA-256 does not match archived PDF")
    if provenance.get("size_bytes") is not None and provenance["size_bytes"] != size:
        raise ValueError("download size does not match archived PDF")
    if provenance["content_type"] != "application/pdf":
        raise ValueError("manifest Content-Type must be application/pdf")
    return {
        "schema_version": "1.0",
        "source_id": source["id"],
        "source_type": source["type"],
        "year": source.get("year"),
        "official_index_url": source["official_index_url"],
        "source_page_url": provenance["source_page_url"],
        "discovered_from": provenance["discovered_from"],
        "pdf_url": provenance["pdf_url"],
        "final_url": provenance["final_url"],
        "source_file_url": provenance["pdf_url"],
        "redirect_chain": provenance["redirect_chain"],
        "discovery_redirect_chain": provenance.get("discovery_redirect_chain", [provenance["source_page_url"]]),
        "content_type": provenance["content_type"],
        "size_bytes": size,
        "original_filename": pdf.name,
        "bytes": size,
        "sha256": digest,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "parser_version": "source-engine-v1.0-reference-only",
        "resulting_record_ids": [],
        "resulting_record_count": 0,
        "status": "NEEDS_REVIEW",
        "published": False,
        "provenance_status": "DISCOVERED",
        "usage_rights_review": "UNREVIEWED",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    source = next((item for item in registry["sources"] if item["id"] == args.source_id), None)
    if source is None:
        parser.error("source-id is not present in final v1.0 registry")
    try:
        manifest = create_manifest(args.pdf, source, args.url)
    except ValueError as exc:
        parser.error(str(exc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"manifest written; sha256={manifest['sha256']}; status=NEEDS_REVIEW; published=false")


if __name__ == "__main__":
    main()
