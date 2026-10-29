#!/usr/bin/env python3
"""Does the local model actually READ the question, or guess from layout?

Sends the same crop at several resize caps and asks the model to transcribe the
first line of the question. Compare against the ground-truth text pulled from the
PDF so the answer is measured, not assumed.
"""
from __future__ import annotations
import base64
import io
import json
import sys
import urllib.request
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

CROP = Path(sys.argv[1] if len(sys.argv) > 1 else
            "/home/selam/roller/web/lgs-ai-coach/lgs_çalışma_soruları/turkce/TU2-TURKCE-Q0001.png")
MODEL = "gemma3:4b"
URL = "http://127.0.0.1:11434/api/chat"


def b64_at(path: Path, max_side: int) -> str:
    im = Image.open(path).convert("RGB")
    if max(im.size) > max_side:
        s = max_side / max(im.size)
        im = im.resize((int(im.width * s), int(im.height * s)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def ask(b64: str) -> str:
    payload = {
        "model": MODEL, "stream": False,
        "messages": [
            {"role": "system", "content": "Görseldeki soruyu oku ve SADECE soru metninin ilk cümlesini yaz. Uydurma; okuyamıyorsan 'OKUYAMIYORUM' yaz."},
            {"role": "user", "content": "Bu sorunun ilk cümlesi nedir?", "images": [b64]},
        ],
        "options": {"temperature": 0.0, "num_ctx": 4096, "num_thread": 4},
    }
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=300)
    return json.loads(r.read().decode())["message"]["content"].strip()


def main():
    im = Image.open(CROP)
    print(f"kırpma: {CROP.name}  {im.width}x{im.height}")
    for cap in (150, 192, 256, 448, 768):
        b64 = b64_at(CROP, cap)
        s = cap / max(im.size) if max(im.size) > cap else 1.0
        dims = f"{int(im.width*s)}x{int(im.height*s)}"
        try:
            out = ask(b64)
        except Exception as e:
            out = f"HATA: {e}"
        print(f"  max_side={cap:>4} ({dims:>9}) -> {out[:110]}")


if __name__ == "__main__":
    main()