#!/usr/bin/env python3
"""
PR teknik incelemesi — Gemini API ile yapilandirilmis (structured) cikti.

Tasarim kararlari (fizibilite raporundan):

1. **Tek dogrulanabilir durum kumesi.** Cikan JSON semaya uymazsa sonucu
   UYGULAMAM: `FIX_REQUIRED` uretmek teknik hatayi gercek bulgu gibi
   gosterirdi. Bu yuzden `REVIEW_UNAVAILABLE` AYRI bir durumdur.
2. **Context budeme zorunlu.** Iki ayri olcum:
   - Buyuklik: PR #4'un gercek diff'i (726.568 karakter) 40.000 karakter
     butceyle gonderildiginde TUM modeller HTTP 503 (UNAVAILABLE) verdi.
   - Kota: ayni diff 20.000 karakterde 429 RESOURCE_EXHAUSTED verdi;
     8.000 karakterde ayni PR basarili incelendi.
   Varsayilan butce 12.000'dir. Asilma durumunda kirpilir ve
   `context_truncated` rapora islenir; PR yorumunda da uyari yazilir.
3. **Diff-only mod.** `--files` verilmezse yalnizca diff gonderilir.
4. **Sifre/PII sizmaz.** Cikti disinda hicbir yere yazilmaz; hata mesajlari
   govdeyi yazmaz.
5. **Shell yok.** Tum alt islemler arguman dizisiyle cagrilir; PR/issue
   govdesi hicbir komuta donusmez.

Kullanim:
    python3 scripts/pr_review/gemini_review.py --pr 4
    python3 scripts/pr_review/gemini_review.py --pr 4 --json-out review.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "abektas/lgs-ai-coach"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Model sirasi: ilki calismazsa siradaki denenir.
#
# Canli kota olcumu (2026-10-03, ayni anahtarla ardisik denemeler):
#   gemini-3.7-flash     -> OK   (500 krk ve 15.000 krk)
#   gemini-3.8-flash     -> HTTP 429 RESOURCE_EXHAUSTED
#   gemini-flash-latest  -> HTTP 429 RESOURCE_EXHAUSTED
# Yani kotasi yeterli olan TEK model 3.7-flash; ilk sira o yapildi.
# `flash-latest` bir ALIAS'tir ve su an 3.8'e isaret ediyor, bu yuzden
# kotasi 3.8 ile ayni sekilde tuki. En SONA atildi: review tutarliligi
# icin asla birincil hedef olmamali, sadece digerleri de dustugunde
# son care olarak denenmeli.
#
# 2.5-* modelleri listede yok: API'ye soruldugunda HTTP 404
# "no longer available to new users" donuyor.
MODEL_CANDIDATES = ["gemini-3.7-flash", "gemini-3.8-flash", "gemini-flash-latest"]

DEFAULT_MAX_CHARS = 12_000
MAX_FILE_CHARS = 8_000
MAX_DESC_CHARS = 6_000

VALID_STATUSES = {"PASS", "FIX_REQUIRED", "PO_DECISION", "REVIEW_UNAVAILABLE"}

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": sorted(VALID_STATUSES)},
        "summary": {"type": "string"},
        "technical_findings": {"type": "array", "items": {"type": "string"}},
        "security_findings": {"type": "array", "items": {"type": "string"}},
        "architecture_findings": {"type": "array", "items": {"type": "string"}},
        "test_findings": {"type": "array", "items": {"type": "string"}},
        "required_actions": {"type": "array", "items": {"type": "string"}},
        "po_decision_required": {"type": "boolean"},
        "po_decision_reason": {"type": "string"},
    },
    "required": [
        "status", "summary", "technical_findings", "security_findings",
        "architecture_findings", "test_findings", "required_actions",
        "po_decision_required",
    ],
}

INSTRUCTIONS = """\
Sen LGS AI Coach projesinde PR teknik incelemesi yapan bir kod inceleyicisisin.

KURALLAR:
- Yalnizca sana verilen DIFF ve dosya iceriklerine dayan. Gorunmeyen bir seyi
  var oldugunu varsayma.
- Urun, mimari, teknoloji, curriculum, privacy/KVKK, maliyet veya kapsam
  kararlari senin alanin DEGIL. Gerekiyorsa status=PO_DECISION don,
  po_decision_required=true ve po_decision_reason doldur.
- status degerleri:
    PASS              = kritik bulgu yok, PR merge edilebilir durumda.
    FIX_REQUIRED      = teknik/guvenlik/test eksigi var, otomatik duzeltilebilir.
    PO_DECISION       = insan karari gerekiyor, otomatik ilerlenemez.
    REVIEW_UNAVAILABLE = cevabin bu inceleme icin yeterli degil.
- Guvenlik bulgusu (secret sizinti, injection, yetki genisletme) daima
  FIX_REQUIRED veya uygunsa PO_DECISION uretir.
- required_actions maddeleri fiilen yapilabilir, somut adimlar olmali;
  en fazla 8 madde.
- Bos liste yerine gercekten bulgu yoksa bos birak.

CIKTI: yalnizca JSON."""


def gh(args: list[str]) -> str:
    """gh CLI'yi arguman dizisiyle cagirir (shell YOK)."""
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, timeout=120, check=False
    )
    if result.returncode != 0:
        # govde/mesaj sizdirilabilir: yalnizca kisa hata sinyali.
        raise RuntimeError(f"gh komutu basarisiz (exit {result.returncode})")
    return result.stdout


def collect_context(pr: int, files: list[str], max_chars: int) -> tuple[str, bool]:
    """PR diff + (varsa) secili dosyalari toplar. (metin, kirpildi_mi)"""
    diff = gh([
        "pr", "diff", str(pr), "--repo", REPO, "--color", "never",
    ])
    meta = json.loads(gh([
        "pr", "view", str(pr), "--repo", REPO,
        "--json", "number,title,body,baseRefName,headRefName",
    ]))

    header = (
        f"# PR #{meta['number']}: {meta['title']}\n"
        f"branch: {meta['headRefName']} -> {meta['baseRefName']}\n\n"
        "## PR aciklamasi\n"
        f"{(meta.get('body') or '')[:MAX_DESC_CHARS]}\n\n"
        "## Degisiklikler (git diff)\n"
    )

    # Diff, butce sigacak sekilde kirpilir; dosyalar ancak kalan yer varsa eklenir.
    remaining = max_chars - len(header)
    truncated = len(diff) > remaining
    if truncated:
        diff_block = diff[:max(remaining, 0)] + "\n\n[DIFF KIRPILDI: butce asildi]\n"
    else:
        diff_block = diff
    parts = [header, diff_block]
    used = len(header) + len(diff_block)

    for path in files:
        # yol sinirini siki tut: disaridan gelen degerler PR'a ait dosyalar
        # olmak zorunda.
        full = Path(path)
        if not full.is_file() or ".." in full.parts:
            continue
        try:
            content = full.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        block = f"\n\n## Dosya: {path}\n{content[:MAX_FILE_CHARS]}"
        if used + len(block) > max_chars:
            parts.append("\n\n[dosyalar butce nedeniyle eklenmedi]")
            truncated = True
            break
        parts.append(block)
        used += len(block)

    return "".join(parts), truncated


def call_gemini(prompt: str, api_key: str, timeout: int) -> dict:
    """Siradaki modelleri dener. HTTP/parse hatasinda sonraki modele gecer."""
    last_error = "bilinmiyor"
    for model in MODEL_CANDIDATES:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": RESPONSE_SCHEMA,
                "temperature": 0,
            },
        }
        request = urllib.request.Request(
            f"{API_BASE}/{model}:generateContent",
            data=json.dumps(payload).encode("utf-8"),
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read())
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)
            parsed["_model"] = model
            return parsed
        except urllib.error.HTTPError as exc:
            # 404 = model kullaniciya kapali, digerleri gecici olabilir.
            last_error = f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = f"ag hatasi: {type(exc).__name__}"
        except (json.JSONDecodeError, KeyError, IndexError):
            last_error = "cevap ayristirilamadi"
    raise RuntimeError(last_error)


def unavailable(summary: str, kind: str, truncated: bool = False) -> dict:
    """Standart 'inceleme yapilamadi' sonucu."""
    return {
        "status": "REVIEW_UNAVAILABLE",
        "summary": summary,
        "error_kind": kind,
        "context_truncated": truncated,
        "technical_findings": [], "security_findings": [],
        "architecture_findings": [], "test_findings": [],
        "required_actions": [], "po_decision_required": False,
        "po_decision_reason": "",
    }


def emit(review: dict, args) -> None:
    """Sonucu stdout'a ve istenirse dosyaya yazar.

    Hata yollari da buradan gecer; boylece `--json-out` her zaman uretilir.
    (Daha once hata donuslerinde dosya yazilmadigi icin sonraki step
    FileNotFoundError ile coktu.)
    """
    rendered = json.dumps(review, ensure_ascii=False, indent=2)
    if args.json_out:
        Path(args.json_out).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--files", nargs="*", default=[])
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--json-out")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        emit(unavailable("GEMINI_API_KEY tanimli degil.", "missing_credentials"), args)
        return 0

    try:
        context, truncated = collect_context(args.pr, args.files, args.max_chars)
    except RuntimeError as exc:
        emit(unavailable(str(exc), "github_fetch_failed"), args)
        return 0

    prompt = (
        f"{INSTRUCTIONS}\n\n"
        f"context_budget_chars: {args.max_chars}\n"
        f"context_truncated: {truncated}\n\n"
        f"{context}"
    )

    try:
        review = call_gemini(prompt, api_key, args.timeout)
    except RuntimeError as exc:
        # KRITIK: API hatasi FIX_REQUIRED DEGILDIR.
        emit(unavailable(
            f"Gemini API cagrisi basarisiz: {exc}", "provider_error", truncated
        ), args)
        return 0

    review.setdefault("context_truncated", truncated)
    # Ikinci savunma hatti: semaya uymayan cikti reddedilir.
    if review.get("status") not in VALID_STATUSES:
        review["status"] = "REVIEW_UNAVAILABLE"
        review["error_kind"] = "schema_violation"

    emit(review, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())