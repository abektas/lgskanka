# MEB Source Ingestion Pilot Implementation Plan

> **For agentic workers:** Execute this plan natively in the current checkout, task by task. Keep each step reviewable. The user explicitly forbids Git commit/push.

**Goal:** Extend the existing Source Engine so only PDFs discovered through registered official MEB pages can be downloaded from the exact `cdn.eba.gov.tr` host, retain verifiable provenance/integrity metadata, extract 2018+ LGS candidates as `NEEDS_REVIEW`, and run a three-PDF 2022/2024/2025 pilot without publishing any question.

**Architecture:** Keep `scripts/source-ingestion/` as the current pipeline and keep its existing registry, canonical schema, duplicate fingerprinting, review queue, API, and verification lifecycle. Add the CDN exception only to link discovery and the download path when accompanied by official-page discovery evidence; keep the generic MEB-host predicate unchanged. Do not alter UI, AI, `/api/questions`, the question store, package dependencies, or create a new Source Engine version.

**Tech Stack:** Python stdlib `urllib`, `hashlib`, `pypdf`; existing Python `unittest`, Node test script, TypeScript, Next.js build.

**Spec:** User request in the current conversation, “MEB Source Engine ingestion pilotundaki mevcut durumu incele ve bir sonraki aşamaya geç.”

## Global Constraints

- Require HTTPS for the registry page, discovery page, PDF URL, and every redirect hop.
- Preserve official page hosts `odsgm.meb.gov.tr`, `meb.gov.tr`, and `mufredat.meb.gov.tr`; preserve existing registry compatibility.
- Treat only exact host `cdn.eba.gov.tr` as a PDF target, and only when an official registered MEB page’s parsed hyperlink discovered it.
- Reject direct/random CDN URLs, redirects to unapproved hosts, non-PDF content type, bad `%PDF-` signature, PDF over 100 MiB, and SHA-256 mismatches.
- Manifest each download with `source_page_url`, `discovered_from`, `pdf_url`, `final_url`, `source_id`, `sha256`, `content_type`, `size_bytes`, and redirect chains.
- Extraction and deterministic validation never set `VERIFIED`; official MEB answer keys remain authoritative; keep `source_verified` and `answer_key_verified` separate.
- Reject `REAL_LGS` before 2018; keep TEOG/pre-2018 material out of canonical LGS staging.
- Keep duplicate fingerprinting and publish duplicate guard. Provenance/technical verification does not mean copyright or reuse permission; record usage-rights review separately as unreviewed.
- Preserve existing user files, six existing identical certificate PDFs/manifests, JSON question store, review queue, UI/AI flow, and unrelated working-tree edits. Do not overwrite or delete these files.
- Do not fetch 2026 `meb.ai` links: that host is outside the explicitly allowed target policy. Report it as excluded by policy, not as an ingested source.
- No Git commit, push, merge, or dependency change.

## Review Focus

1. **Direct/random `cdn.eba.gov.tr` URL with no discovery evidence** — downloader rejects before network access.
2. **Official page → CDN → another domain, or any HTTP redirect** — redirect handler rejects and returns the recorded hop/reason without saving partial files.
3. **HTML, wrong content type, malformed PDF header, oversize, or mismatched SHA** — reject download or manifest/extraction with a clear reason; never leave a final archive file.
4. **Scanned/image-only or malformed booklet text, ambiguous question/answer numbering, incomplete A–D options** — retain extraction diagnostics and explicit `NEEDS_REVIEW` reasons, including when candidate count is zero.
5. **Pre-2018, answer key not independently verified, any missing human check, or duplicate fingerprint** — canonical validation/publish refuses `VERIFIED` promotion.

## File Structure

- Modify `scripts/source-ingestion/download_official_pdfs.py`: discovery evidence, safe redirect chain, exact CDN exception, content/header/size/hash validation, booklet selection and manifest generation.
- Modify `scripts/source-ingestion/create_ingestion_manifest.py`: same canonical provenance contract for manifest validation/creation; separate source provenance from usage-rights state.
- Modify `scripts/source-ingestion/extract_pdf_candidates.py`: verify the expanded manifest, preserve source provenance, isolate answer-key candidates to explicit answer-key content, and record document/question-level review reasons.
- Modify `scripts/source-ingestion/canonical_schema.json` and `scripts/source-ingestion/validate_canonical.py`: require/validate new provenance fields and maintain separate answer checks and 2018 floor.
- Modify or add `tests/source-ingestion/test_pipeline.py` and `tests/source-ingestion/test_source_trust.py`: regression matrix with fake responses/openers; no test contacts the network.
- Add real pilot PDFs, manifests and staging under root `data/questions/archive/`, `data/questions/manifests/`, and `data/questions/staging/`; update root `data/questions/review-queue.json` only with the generated pilot review queue.
- Update `docs/source-engine-integration.md` with exact pilot scope/results, scanned/empty extraction outcomes, technical-vs-rights distinction, and the 2026 host-policy exclusion. Do not alter `data/source-engine/` reference-package contents or the application/API flow.

## Tasks

### Task 1: Lock trust policy and manifest contract with regression tests

**Interfaces:** Add discovery records with `source_id`, `discovered_from` (registered index URL), `source_page_url` (official page where the anchor was parsed), `pdf_url` (anchor target), and the page’s redirect chain. Pass this record to `download_pdf`; a bare URL is insufficient. The generic `official_host()` remains limited to MEB domains; exact CDN matching is a separate predicate.

- [ ] Add tests for official MEB page → exact `cdn.eba.gov.tr` accepted and a random CDN URL rejected before opener use.
- [ ] Add fake redirect tests for HTTPS MEB→CDN acceptance, CDN→foreign-host rejection, and HTTP rejection; assert redirect hops are recorded.
- [ ] Add download tests for PDF Content-Type, `%PDF-` magic, size cap, immutable/idempotent archive, and SHA-256.
- [ ] Extend manifest tests to require all listed provenance/integrity fields and distinguish technical status from rights review.
- [ ] Run `python3 tests/source-ingestion/test_source_trust.py -v`; confirm the new cases fail before implementation.
- [ ] Implement the smallest changes in downloader/manifest functions to pass those tests. Preserve the 100 MiB limit and atomic temporary-file cleanup.

### Task 2: Preserve extraction diagnostics and publication gates

- [ ] Add tests for zero-text/scanned input, no detected questions, missing options, ambiguous answer-key text, and explicit `NEEDS_REVIEW` reasons; assert zero candidates remain zero rather than being silently presented as successful extraction.
- [ ] Add tests that extracted candidate records remain `NEEDS_REVIEW`, cannot transition to `VERIFIED` without both source and answer-key checks, reject `REAL_LGS` pre-2018, and refuse duplicate verified questions.
- [ ] Update canonical source provenance fields and extraction reason fields without renaming the existing schema version or changing `/api/questions`.
- [ ] Make answer-key parsing candidate-only and conservative; never set canonical `answer_key.answer` from PDF text extraction.
- [ ] Run `npm run test:source`; all existing and added source tests must pass.

### Task 3: Run the real, limited MEB PDF pilot

- [ ] Use one numeric booklet per year: 2022 `SAYISAL`, 2024 `SAYISAL`, 2025 `SAYISAL_A`. Expected official page anchors resolve respectively through the registered ÖDSGM pages to `cdn.eba.gov.tr`; save the observed URLs, final URLs, redirect chains, headers, sizes, and hashes.
- [ ] Run the downloader separately for `MEB-LGS-2022`, `MEB-LGS-2024`, and `MEB-LGS-2025`, selecting the named booklet from page-discovered links. Do not pass a hand-entered CDN URL to the downloader.
- [ ] Verify each downloaded PDF header, Content-Type, exact byte count, SHA-256, and manifest fields before extraction. Keep source bytes immutable and distinct from the existing invalid certificate fixtures.
- [ ] Run `pypdf` extraction for each manifest. Save candidate JSON and all warnings/review reasons; build one combined review queue using the existing fingerprint function.
- [ ] Run deterministic canonical validation on each staging file. Keep question count, answer-key candidate count, `NEEDS_REVIEW` count, and `VERIFIED=0` explicit. Do not publish to `data/questions/questions.json`.
- [ ] If a live PDF fails extraction, report the failure and continue the other selected years. Do not convert missing/ambiguous output into a successful candidate.

### Task 4: Update integration record and run required verification

- [ ] Amend `docs/source-engine-integration.md` to distinguish the original failed CDN attempt, the six current identical scanned certificate artifacts (not LGS pilot downloads), and the new controlled pilot. Record source attribution and rights status separately.
- [ ] Run exactly: `npm run validate:sources`, `npm run test:source`, `npm run test:ai`, `npx tsc --noEmit`, `npm run build`, and `git diff --check`.
- [ ] Review all staged/unstaged/untracked paths with `git status`; preserve all pre-existing untracked and modified files. Make no commit or push.

## Definition of Done

- The exact trust and regression behaviors above pass; arbitrary CDN URLs never gain general allowlist status.
- Every successfully downloaded pilot PDF has complete provenance, redirect, Content-Type, size, magic, and SHA-256 evidence in a manifest.
- Every extraction outcome (including zero text/questions) is explicit and remains unpublished `NEEDS_REVIEW`; no result is promoted to `VERIFIED`.
- Selected-year download/extraction counts and failures are reported from produced artifacts, not inferred from discovery links.
- All six user-requested commands run and their real outcomes are reported; no UI/AI/API behavior changes; no commit/push.
