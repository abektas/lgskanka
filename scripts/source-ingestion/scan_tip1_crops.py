#!/usr/bin/env python3
"""Pixel-scan validation of v21 crops (no vision model available).

Checks per PNG:
  * top band (first 12 px rows): dark pixels => header bleed or cut content
  * bottom band (last 12 px rows): dark pixels => footer/page-number bleed
  * left/right bands: near-edge darkness => cut content
  * content presence: enough dark pixels in the middle
Reports the worst offenders per subject folder.
"""
from __future__ import annotations

import sys
from pathlib import Path
from PIL import Image

BAND = 12
DARK = 160          # threshold for "dark" pixel
EDGE_FRACTION = 0.02


def scan(png: Path) -> dict:
    img = Image.open(png).convert("L")
    w, h = img.size
    px = img.load()
    if px is None:
        raise RuntimeError(f"cannot load pixels: {png}")

    def band_dark(x0: int, y0: int, x1: int, y1: int) -> int:
        count = 0
        for y in range(y0, y1):
            for x in range(x0, x1):
                v = px[x, y]
                if isinstance(v, tuple):
                    v = v[0]
                if v < DARK:
                    count += 1
        return count

    top = band_dark(0, 0, w, min(BAND, h))
    bottom = band_dark(0, max(0, h - BAND), w, h)
    left = band_dark(0, 0, max(2, int(w * EDGE_FRACTION)), h)
    right = band_dark(max(0, w - int(w * EDGE_FRACTION)), 0, w, h)
    mid = band_dark(0, h // 3, w, 2 * h // 3)
    return {"top": top, "bottom": bottom, "left": left, "right": right,
            "mid": mid, "w": w, "h": h}


def main(folder: Path, sample: int = 200) -> int:
    pngs = sorted(folder.glob("*.png"))
    if not pngs:
        print("no PNGs")
        return 1
    step = max(1, len(pngs) // sample)
    picked = pngs[::step][:sample]
    worst = {"top": [], "bottom": [], "left": [], "right": []}
    empty_mid = []
    for png in picked:
        r = scan(png)
        for k in ("top", "bottom", "left", "right"):
            worst[k].append((r[k], png.name))
        if r["mid"] < 50:
            empty_mid.append(png.name)
    for k, rows in worst.items():
        rows.sort(reverse=True)
        print(f"--- worst {k} band ---")
        for count, name in rows[:8]:
            print(f"  {count:8d}  {name}")
    print("--- near-empty mid ---")
    for name in empty_mid[:10]:
        print(f"  {name}")
    print(f"sampled {len(picked)} of {len(pngs)} PNGs")
    return 0


if __name__ == "__main__":
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else "ingilizce")
    sys.exit(main(folder))
