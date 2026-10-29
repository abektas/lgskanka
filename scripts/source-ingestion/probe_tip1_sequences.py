#!/usr/bin/env python3
"""Probe: key-page pair sequences (row-major + reset) and question anchor sequences."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import extract_tip1_v21 as E

QRE = re.compile(r"^(\d{1,2})[.)]?$")


def probe_key(pdf, pno):
    pages = E.load_book(E.INPUT_DIR / pdf)
    p = pages[pno - 1]
    pairs = E.parse_pairs(p["rects"])
    rows = {}
    for r in p["rects"]:
        m = QRE.fullmatch(r["text"])
        if m and 1 <= int(m.group(1)) <= 90:
            rows.setdefault(round(r["y0"] / 3), []).append((r["x0"], int(m.group(1))))
    seq = []
    for band in sorted(rows):
        seq.extend(q for _, q in sorted(rows[band]))
    resets = [i for i in range(1, len(seq)) if seq[i] == 1 and seq[i - 1] != 0]
    blocks = []
    start = 0
    for i in resets:
        blocks.append(seq[start:i])
        start = i
    blocks.append(seq[start:])
    print(f"{pdf} p{pno}: total={len(seq)} blocks={[len(b) for b in blocks]} "
          f"block_heads={[b[0] for b in blocks]} tails={[b[-1] for b in blocks]}")
    # unit labels on the page
    for l in p["lines"]:
        if re.match(r"^(\d{1,2}[.)]\s*(Ünite|Tema))|^Unit \d+$", l["text"], re.I):
            print(f"   label y={l['y0']:.0f} x={l['x0']:.0f}: {l['text']!r}")


def probe_anchors(pdf, p_from, p_to, note=""):
    pages = E.load_book(E.INPUT_DIR / pdf)
    print(f"\n--- {pdf} anchors p{p_from}-{p_to} {note} ---")
    for p in pages[p_from - 1:p_to]:
        W, H = p["size"]
        anchors = E.anchors_of(p["lines"], W)
        hs = E.header_subject(p["lines"])
        covers = [l["text"] for l in p["lines"]
                  if re.match(r"^(\d{1,2}[.)]\s*(Ünite|Tema))|^Unit \d+$", l["text"], re.I)
                  and l["y0"] < H / 2]
        if anchors or hs or covers:
            nums = [a["num"] for a in anchors]
            print(f"  p{p['index']}: hdr={hs} covers={covers} anchors={nums}")


if __name__ == "__main__":
    for pdf, pnos in [("cal05.pdf", [100, 183, 343, 344]),
                      ("cal01.pdf", [306, 307, 308]),
                      ("cal02.pdf", [291, 292]),
                      ("cal06.pdf", [228, 229, 230])]:
        for pno in pnos:
            probe_key(pdf, pno)
    probe_anchors("cal05.pdf", 7, 60, "(inkilap units)")
    probe_anchors("cal05.pdf", 101, 115, "(din units)")
    probe_anchors("cal05.pdf", 185, 215, "(english units)")
