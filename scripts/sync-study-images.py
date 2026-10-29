#!/usr/bin/env python3
"""Sync study-question images from the workspace into the app's public folder.

The app serves images from `public/study/{subject}-{filename}.png` and reads
question metadata from the workspace manifests (`lgs_çalışma_soruları/<subject>/manifest*.json`).
This script keeps the two in sync:

  * copies every manifest-referenced PNG from the workspace (overwriting, so the
    served image always matches the manifest's crop)
  * deletes images in `public/study/` that no manifest references anymore
    (e.g. questions that were removed from the workspace)

Rules mirrored from `app/api/study/route.ts` — keep them in step:
  * `published: false` questions are never served
  * `cancelledInSource: true` questions are never served

Usage:
    python3 scripts/sync-study-images.py            # apply
    python3 scripts/sync-study-images.py --dry-run  # only report
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "lgs_çalışma_soruları"
PUBLIC_STUDY = ROOT / "public" / "study"


def referenced_images() -> dict[str, set[str]]:
    """subject -> set of `{subject}-{filename}` keys that must exist in public/study."""
    out: dict[str, set[str]] = {}
    if not WORKSPACE.is_dir():
        sys.exit(f"Workspace folder not found: {WORKSPACE}")

    for subj_dir in sorted(WORKSPACE.iterdir()):
        if not subj_dir.is_dir():
            continue
        keys: set[str] = set()
        for manifest in sorted(subj_dir.glob("manifest*.json")):
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                print(f"  ! skipping unreadable {manifest}: {exc}")
                continue
            for q in data.get("questions", []):
                if not (q.get("q") or q.get("questionNumber")):
                    continue
                if q.get("published") is False:
                    continue
                if q.get("cancelledInSource"):
                    continue
                filename = os.path.basename(q.get("file") or "")
                if filename:
                    keys.add(f"{subj_dir.name}-{filename}")
        out[subj_dir.name] = keys
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report only")
    args = parser.parse_args()

    referenced = referenced_images()

    copied = deleted = 0
    for subject, keys in sorted(referenced.items()):
        # key -> workspace filename (key is `{subject}-{filename}`)
        want = {k: k[len(subject) + 1 :] for k in keys}
        existing = {
            f
            for f in os.listdir(PUBLIC_STUDY)
            if f.startswith(f"{subject}-") and f.endswith(".png")
        }

        to_copy = sorted(set(want))
        to_delete = sorted(existing - set(want))

        print(f"{subject}: kopyala={len(to_copy)} sil={len(to_delete)}")
        if args.dry_run:
            for f in to_delete[:5]:
                print(f"    silinecek örnek: {f}")
            copied += len(to_copy)
            deleted += len(to_delete)
            continue

        for key in to_copy:
            src = WORKSPACE / subject / want[key]
            dst = PUBLIC_STUDY / key
            if src.exists():
                shutil.copy2(src, dst)
            else:
                print(f"    ! kaynak PNG yok: {src}")
        for filename in to_delete:
            (PUBLIC_STUDY / filename).unlink()

        copied += len(to_copy)
        deleted += len(to_delete)

    mode = "DRY-RUN" if args.dry_run else "UYGULANDI"
    print(f"\n{mode}: kopyalanan={copied} silinen={deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
