#!/usr/bin/env python3
"""Promote only manually verified staging records to server-side API JSON."""
import argparse
import json
from pathlib import Path

from validate_canonical import REQUIRED_CHECKS, canonical_fingerprint, validate_record


def api_row(record):
    source, question = record["source"], record["question"]
    mappings = record["curriculum"]
    layer, mapping = next((key, value) for key, value in mappings.items() if value.get("status") == "VERIFIED")
    return {
        "id": record["id"], "sourceId": source["source_id"], "sourceType": source["source_type"],
        "year": source.get("year"), "booklet": source["booklet"], "subject": question["subject"] or mapping["subject"],
        "grade": 8, "questionNumber": source["question_number"], "stem": question["stem"], "options": question["options"],
        "answer": record["answer_key"]["answer"], "solution": record.get("solution", ""), "status": "VERIFIED",
        "curriculum": {"layer": layer, "subject": mapping["subject"], "unit": mapping["unit"], "topic": mapping["topic"], "learningOutcome": mapping["learning_outcome"], "skill": mapping["skill"], "version": mapping["version"]},
        "verification": {key: True for key in REQUIRED_CHECKS}, "sourceHash": source["source_sha256"],
    }


def publish(payload):
    records = payload.get("records", [])
    published = []
    seen_fingerprints = {}
    for record in records:
        if record.get("status") != "VERIFIED":
            continue
        errors = validate_record(record, require_verified=True)
        if errors:
            raise ValueError(f"refusing malformed VERIFIED record {record.get('id')}: {'; '.join(errors)}")
        fingerprint = canonical_fingerprint(record)
        if fingerprint in seen_fingerprints:
            raise ValueError(f"refusing duplicate VERIFIED records {seen_fingerprints[fingerprint]} and {record.get('id')}")
        seen_fingerprints[fingerprint] = record.get("id")
        published.append(api_row(record))
    return published


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("staging", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.staging.read_text(encoding="utf-8"))
    rows = publish(payload)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"published {len(rows)} manually VERIFIED record(s); answer keys remain server-side")

if __name__ == "__main__": main()
