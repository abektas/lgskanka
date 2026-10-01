#!/usr/bin/env python3
"""Validate the final v1.0 source registry against the LGS/MEB source policy."""
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data/source-engine/config/source-registry.json"
ALLOWED_HOSTS = {"meb.gov.tr", "meb.k12.tr"}
SOURCE_TYPES = {"REAL_LGS", "MEB_SAMPLE", "MEB_BOOK", "MEB_CURRICULUM", "VERIFIED_EXTERNAL", "AI_GENERATED"}


def official_host(host: str) -> bool:
    return any(host == domain or host.endswith("." + domain) for domain in ALLOWED_HOSTS)


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    sources = data.get("sources")
    if not isinstance(sources, list):
        return ["sources must be an array"]
    seen: set[str] = set()
    for source in sources:
        sid = source.get("id", "<missing>")
        if sid in seen:
            errors.append(f"duplicate source id: {sid}")
        seen.add(sid)
        kind = source.get("type")
        if kind not in SOURCE_TYPES:
            errors.append(f"invalid source type for {sid}: {kind}")
        if kind == "REAL_LGS" and (not isinstance(source.get("year"), int) or source["year"] < 2018):
            errors.append(f"pre-2018 or missing REAL_LGS year: {sid}")
        url = source.get("official_index_url", "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or not official_host(parsed.hostname.lower()):
            errors.append(f"URL must use an official MEB HTTPS host: {sid}")
    return errors


if __name__ == "__main__":
    try:
        errors = validate(json.loads(REGISTRY.read_text(encoding="utf-8")))
    except Exception as exc:
        print(f"registry could not be read: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(1)
    print(f"OK: {len(json.loads(REGISTRY.read_text(encoding='utf-8'))['sources'])} official source records")
