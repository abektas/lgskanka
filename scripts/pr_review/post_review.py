#!/usr/bin/env python3
"""
PR inceleme sonucunu GitHub'a yazar.

Kurallar:
- Yalnizca OZET yorumu yazilir; ham JSON loga basilmaz (ogrenci verisi /
  uzunluk / sirlilik riski).
- Idempotent: ayni sonuc (head sha + status) zaten yorumlandiysa tekrar
  yorum yazilmaz. Bu, `synchronize` event'inin tekrarinda spam'i onler.
- Otomatik merge/deploy YOK; yalnizca yorum ve etiket.
- FIX_REQUIRED icin otomatik yeni kosu YOK (Faz 1 kapsami disi).
  Otomasyon burada durur, insan devreye girer.
- Tum alt islemler arguman dizisiyle (shell yok).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = "abektas/lgs-ai-coach"
MARKER = "<!-- nuli-gemini-review -->"
STATE_LABEL = "gemini-review"
MAX_BODY_CHARS = 60_000

ICON = {"PASS": "✅", "FIX_REQUIRED": "🔧", "PO_DECISION": "🧑‍⚖️", "REVIEW_UNAVAILABLE": "⚠️"}

HEADLINE = {
    "PASS": "PASS — kritik bulgu yok, insan incelemesine hazir.",
    "FIX_REQUIRED": "FIX_REQUIRED — teknik/guvenlik/test eksigi var.",
    "PO_DECISION": "PO_DECISION — bu konu insan karari gerektiriyor.",
    "REVIEW_UNAVAILABLE": "REVIEW_UNAVAILABLE — inceleme calistirilamadi (bulgu DEGIL).",
}


def gh(args: list[str], stdin: str | None = None) -> str:
    result = subprocess.run(
        ["gh", *args], input=stdin, capture_output=True, text=True,
        timeout=120, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh basarisiz (exit {result.returncode})")
    return result.stdout


def section(title: str, items: list[str]) -> str:
    if not items:
        return ""
    lines = "\n".join(f"- {item}" for item in items)
    return f"\n\n**{title}**\n{lines}"


def render(review: dict, head_sha: str, model: str) -> str:
    status = review.get("status", "REVIEW_UNAVAILABLE")
    icon = ICON.get(status, "⚠️")
    parts = [
        MARKER,
        f"## {icon} Gemini teknik incelemesi — {status}",
        "",
        HEADLINE.get(status, ""),
        "",
        f"**Commit:** `{head_sha[:7]}` · **Model:** `{model or 'bilinmiyor'}`",
    ]
    if review.get("context_truncated"):
        parts.append(
            "\n> ⚠️ Diff bütçeye sığmadığı için kırpılarak incelendi. "
            "Kapsam dışı kalan bölümler taranmamış olabilir."
        )
    if review.get("summary"):
        parts.append(f"\n{review['summary']}")

    parts.append(section("Teknik bulgular", review.get("technical_findings") or []))
    parts.append(section("Güvenlik bulgular", review.get("security_findings") or []))
    parts.append(section("Mimari bulgular", review.get("architecture_findings") or []))
    parts.append(section("Test bulgular", review.get("test_findings") or []))
    parts.append(section("Gerekli aksiyonlar", review.get("required_actions") or []))

    if review.get("po_decision_required"):
        parts.append("\n\n**PO kararı gerekli:**")
        if review.get("po_decision_reason"):
            parts.append(f"\n{review['po_decision_reason']}")

    if status == "REVIEW_UNAVAILABLE":
        parts.append(
            "\n\n> Bu sonuç **bir bulgu değildir**. İnceleme teknik bir "
            "nedenle yapılamadı; elle inceleme gerekir."
        )
        if review.get("error_kind"):
            parts.append(f"\n> Hata türü: `{review['error_kind']}`")

    parts.append(
        "\n\n---\n<sub>Otomatik inceleme. Merge/deploy yapılmaz. "
        "`FIX_REQUIRED` durumunda otomatik düzeltme koşusu **başlatılmaz**.</sub>"
    )
    body = "\n".join(parts)
    return body[:MAX_BODY_CHARS]


def already_posted(pr: int, head_sha: str, status: str) -> bool:
    """Ayni commit + ayni sonuc zaten yorumlandiysa True."""
    try:
        comments = json.loads(gh([
            "api", f"repos/{REPO}/issues/{pr}/comments", "--paginate",
            "--jq", "[.[].body]",
        ]))
    except RuntimeError:
        return False
    for body in comments:
        if MARKER in body and head_sha[:7] in body and status in body:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--head-sha", default="")
    args = parser.parse_args()

    review = json.loads(Path(args.json).read_text(encoding="utf-8"))
    status = review.get("status", "REVIEW_UNAVAILABLE")
    model = review.get("_model", "")
    head_sha = args.head_sha or review.get("_head_sha", "")

    if not head_sha:
        # PR'nin guncel head'i: yorumun hangi commit'i anlattigini dogru
        # etiketlemek icin gerekli.
        meta = json.loads(gh([
            "pr", "view", str(args.pr), "--repo", REPO, "--json", "headRefOid",
        ]))
        head_sha = meta.get("headRefOid", "")

    if already_posted(args.pr, head_sha, status):
        print(f"ayni sonuc zaten yorumlandi: {status}")
        return 0

    gh(["pr", "comment", str(args.pr), "--repo", REPO,
        "--body", render(review, head_sha, model)])

    # Etiket state tasimasi. Etiket yoksa `gh label create` ile acilir.
    try:
        gh(["issue", "edit", str(args.pr), "--repo", REPO, "--add-label", STATE_LABEL])
    except RuntimeError:
        try:
            gh(["label", "create", STATE_LABEL, "--repo", REPO,
                "--description", "Gemini teknik incelemesi tamamlandi",
                "--color", "5319E7"])
            gh(["issue", "edit", str(args.pr), "--repo", REPO, "--add-label", STATE_LABEL])
        except RuntimeError:
            print("etiket eklenemedi (etiket yoksa tekrar denemek icin: gh label create gemini-review)")
            return 0

    print(f"yorum yazildi: {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())