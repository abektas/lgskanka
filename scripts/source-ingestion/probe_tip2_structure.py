#!/usr/bin/env python3
"""Quick structure probe for tip_2 workbooks (no cropping)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import extract_tip2_v21 as E

path = E.INPUT_DIR / (sys.argv[1] if len(sys.argv) > 1 else "cal07.pdf")
pages = E.load_book(path)
toc = E.parse_toc_provinces(pages)
print("TOC provinces:", toc)
print()
keys = [p["index"] for p in pages if E.is_key_page(p)]
print("Key pages:", keys)
print()
if toc:
    first_name, first_pg = toc[0]
    print(f"First province: {first_name} (printed p{first_pg})")
    for p in pages[first_pg + 5:first_pg + 10]:
        head = " | ".join(l["text"][:50] for l in p["lines"][:3])
        print(f"  p{p['index']}: {head}")
    # Subject headers in first province section
    print()
    print("Subject headers detected:")
    for p in pages[first_pg:first_pg + 30]:
        hs = E.detect_subject_header(p["lines"])
        if hs:
            head = p["lines"][0]["text"][:40] if p["lines"] else ""
            print(f"  p{p['index']}: {hs} ({head!r})")
