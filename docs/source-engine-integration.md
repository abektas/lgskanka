# MEB Source Engine integration (final v1.0)

## Scope and provenance

The integration uses only `data/source-engine/`, copied from `LGS_MEB_SOURCE_ENGINE_FINAL_v1.0.zip`; its `FILE_MANIFEST.json` verifies the copied reference files. No earlier source-engine package is included. The registry is a discovery index, not evidence that a PDF, answer key, curriculum mapping, or question has been independently verified. No source PDFs or question records were present at integration time.

Supported source types are `REAL_LGS`, `MEB_SAMPLE`, `MEB_BOOK`, `MEB_CURRICULUM`, `VERIFIED_EXTERNAL`, and `AI_GENERATED`. Canonical LGS records begin in 2018. TEOG and earlier central exam content are excluded. AI-generated records require an `AI-` source identity and cannot be labeled as MEB material. Curriculum is represented independently in `LGS_REFERENCE_2018_PLUS` and `CURRENT_TYMM`, with the intended chain Ders → Ünite → Konu → Kazanım → Beceri.

Question lifecycle values are `DRAFT`, `EXTRACTED`, `AUTO_CHECKED`, `NEEDS_REVIEW`, `VERIFIED`, and `REJECTED`. Extraction and deterministic checks never set `VERIFIED`. Publication requires manual provenance/answer/curriculum/solution/duplicate checks. Official LGS/MEB answer keys are authoritative; generated or inferred answers are not substitutes.

## Ingestion and review

Run `npm run validate:sources` to validate the final registry. To create a manifest for a locally obtained PDF:

```sh
python3 scripts/source-ingestion/create_ingestion_manifest.py ./source.pdf \
  --source-id MEB-LGS-2025 \
  --url 'https://odsgm.meb.gov.tr/www/lgs-kapsamindaki-merkezi-sinav-tamamlandi-soru-kitapciklari-yayimlandi/icerik/1446' \
  --out ./data/questions/manifests/MEB-LGS-2025.json
```

The tool only accepts the exact registered HTTPS index URL on an official `meb.gov.tr` or `meb.k12.tr` host, limits the local PDF to 100 MiB, computes SHA-256, and writes an unpublished `NEEDS_REVIEW` manifest. It does not download or parse PDFs. Candidate extraction is intentionally a separate future step. `build_review_queue.py` writes all checks false and leaves all items in `NEEDS_REVIEW`; likely duplicate candidates are flagged for manual resolution.

## API and answer handling

- `GET /api/questions?subject=...&layer=...` returns only structurally valid `VERIFIED` rows from the server-side JSON store. It excludes answer keys, verification data, and source hashes. The store is currently empty, so the API returns `{ items: [], count: 0 }`.
- `POST /api/questions` accepts `{ "questionId": "...", "answer": "..." }`. It evaluates against the server-side answer key and returns only `{ "correct": boolean }`; it does not return the correct answer.
- `/api/ai` remains unchanged and independent. AI analysis does not promote content to verified provenance.

The current application has no database driver or configured database. `db/001_question_bank.sql` and its down migration are reviewable PostgreSQL schema files only; neither was applied. The schema constrains the allowed source/status values, official MEB host URLs, 2018+ REAL_LGS years, SHA-256 format, AI identity, and the required verification checks for `VERIFIED`. The down migration drops the two new tables, so use it only if their imported records are intentionally disposable or backed up.

The existing study flow already sends media for transient AI analysis. This integration clears the selected photo and voice transcript from component state after both success and failure. No student identifiers or student content were added to fixtures or the repository.

## Remaining operational work

Obtain official source documents, parse them in a separately reviewed ingestion step, compare real answer keys, map both curriculum layers with official evidence, perform duplicate checks, and manually review each record. Connect a database and apply migrations only after reviewing the target environment, then replace the empty JSON store with a server-only data-access layer. No records are currently available for practice.

## Controlled MEB ingestion pipeline

The canonical staging pipeline now lives in `scripts/source-ingestion/`:

1. `download_official_pdfs.py --source-id MEB-LGS-2025 --booklet SAYISAL_A --max-pdfs 1` fetches only PDF links discovered from that source's exact registered HTTPS index URL, selecting the booklet from the official page's own anchor text and failing loudly when the requested booklet code is not registered for that source or matches no discovered PDF. The index and PDF URLs, including redirects, must remain on `meb.gov.tr` or `meb.k12.tr` hosts; each file is capped at 100 MiB and at most three PDFs can be selected per run. Original bytes go under `data/questions/archive/`; SHA-256 manifests under `data/questions/manifests/` include the registered index and resolved file URL.
2. `extract_pdf_candidates.py <pdf> --source-id MEB-LGS-2025 --manifest data/questions/manifests/<manifest>.json --booklet SAYISAL_A --out data/questions/staging/<id>.json` uses `pypdf` text extraction and conservative question/option segmentation. It records page ranges, text density/option warnings and possible answer-key strings; it never sets an official answer, curriculum mapping, review check, or `VERIFIED` state.
3. `build_review_queue.py <staging-file> --out data/questions/review-queue.json` preserves the existing normalized stem/options duplicate fingerprint and creates all-false review checks. `validate_canonical.py <staging-file>` checks deterministic structure and source/year policy. `publish_verified.py <staging-file> --out data/questions/questions.json` promotes only records already in `VERIFIED` and meeting every human-review gate.

Canonical staging is defined by `scripts/source-ingestion/canonical_schema.json`. `answer_key.source_verified` and `answer_key.answer_key_verified` are separate from the `checks.answer_key_source_verified` and `checks.answer_key_verified` review flags. Only an official MEB answer key can populate the canonical answer; detected text is a candidate only. Both curriculum layers remain represented; at least one evidence-backed mapping must be manually verified before promotion. The API continues to expose no answer, source hash, or verification flags and now also requires the independent answer-key-source check.

Pilot attempt on 2026-09-30: the pipeline fetched exactly the six registered index pages for 2022–2026 LGS and the MEB sample archive, and inspected at most one PDF per source. It discovered 12 explicitly labelled question/booklet PDF links hosted on `cdn.eba.gov.tr` (2022: 2, 2024: 2, 2025: 8); all were skipped because that host is outside the current `meb.gov.tr` / `meb.k12.tr` allowlist. No allowlisted direct question PDF was found on the other three pages. One first-pass broad-link defect also matched a shared certificate PDF; those agent-created invalid archive files/manifests were removed, and contextual anchor filtering plus a regression test now excludes unrelated PDFs. Final pilot result: 0 PDFs downloaded, 0 manifests, 0 extracted question records, 0 VERIFIED, 0 NEEDS_REVIEW; `data/questions/questions.json` remains empty. No URL outside the registry-linked MEB pages and the allowlisted hosts was fetched. PDF OCR is not included: image-only/scanned pages and low-text/ambiguous questions are flagged for human review, and the environment has no OCR dependency configured.
