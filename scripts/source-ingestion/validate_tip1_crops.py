#!/usr/bin/env python3
"""Text-level validation of v21 crops.

For every question in a subject manifest, re-open the question's own source
PDF page (manifest.sourceFile) and verify inside clipRectPt:
  * the question's own number rect ('N.') is present;
  * at least one option marker ('A)' or 'A)') is present below the stem;
  * no OTHER question's anchor lies inside the rect (no bleed).
Prints violations only, then a summary.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import extract_tip1_v21 as E


def main(slug: str) -> int:
    repo = Path("/home/selam/roller/web/lgs-ai-coach")
    manifest = json.load(open(repo / slug / "manifest.json", encoding="utf-8"))
    loaded: dict[str, list] = {}
    violations = []
    checked = 0
    for q in manifest["questions"]:
        fname = q.get("sourceFile")
        if not fname:
            violations.append((q["file"], "no sourceFile in manifest"))
            continue
        if fname not in loaded:
            loaded[fname] = E.load_book(E.INPUT_DIR / fname)
        p = loaded[fname][q["page"] - 1]
        rect = q["visual"]["clipRectPt"]
        inside = [r for r in p["rects"]
                  if rect["x0"] <= r["x0"] and r["x1"] <= rect["x1"]
                  and rect["y0"] <= r["y0"] and r["y1"] <= rect["y1"]]
        own = [r for r in inside if E.ANCHOR_RE.fullmatch(r["text"])
               and int(r["text"][:-1]) == q["questionNumber"]]
        opts = [r for r in inside if r["text"].startswith("A)")]
        foreign = [r for r in inside if E.ANCHOR_RE.fullmatch(r["text"])
                   and int(r["text"][:-1]) != q["questionNumber"]]
        checked += 1
        if not own:
            violations.append((q["file"], "missing own anchor"))
        if not opts:
            violations.append((q["file"], "missing A) option"))
        if foreign:
            violations.append((q["file"],
                               f"foreign anchors {[r['text'] for r in foreign]}"))
    for f, why in violations[:60]:
        print(f"  {f}: {why}")
    print(f"checked {checked}, violations {len(violations)}")
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "ingilizce"))
