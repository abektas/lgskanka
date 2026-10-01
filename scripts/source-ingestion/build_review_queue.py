#!/usr/bin/env python3
"""Build a review queue; extraction never implies verification or publication."""
import argparse
import json
import hashlib
import re
from pathlib import Path

REQUIRED_CHECKS = ["source_verified", "year_verified", "booklet_verified", "question_number_verified", "text_verified", "options_verified", "answer_key_source_verified", "answer_key_verified", "curriculum_verified", "solution_verified", "duplicate_checked"]


def fingerprint(block: dict) -> str | None:
    question = block.get("question", block)
    stem = question.get("stem") if isinstance(question, dict) else None
    options = question.get("options") if isinstance(question, dict) else None
    if not isinstance(stem, str) or not isinstance(options, (dict, list)):
        return None
    normalized = re.sub(r"\s+", " ", stem).strip().casefold()
    payload = json.dumps([normalized, options], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build(data: dict) -> dict:
    blocks = data.get("blocks", data.get("records", []))
    seen: dict[str, list[int]] = {}
    for index, block in enumerate(blocks):
        candidate = fingerprint(block)
        if candidate:
            seen.setdefault(candidate, []).append(index)
    items = []
    for index, block in enumerate(blocks):
        candidate = fingerprint(block)
        question = block.get("question", block)
        source = block.get("source", {})
        items.append({
            "record_id": block.get("id"),
            "source_id": source.get("source_id", block.get("source_id")) if isinstance(source, dict) else block.get("source_id"),
            "question_number": block.get("question_number") or (block.get("source", {}).get("question_number") if isinstance(block.get("source"), dict) else None),
            "page_start": question.get("page_start"),
            "page_end": question.get("page_end"),
            "status": "NEEDS_REVIEW",
            "candidate_fingerprint": candidate,
            "possible_duplicate_indices": [other for other in seen.get(candidate, []) if other != index] if candidate else [],
            "checks": {key: False for key in REQUIRED_CHECKS},
        })
    return {"count": len(items), "items": items}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("questions_json", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = build(json.loads(args.questions_json.read_text(encoding="utf-8")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"review items: {result['count']}")


if __name__ == "__main__":
    main()
