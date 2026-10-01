# SDD ledger — plan: docs/superpowers/plans/2026-09-30-meb-source-ingestion-pilot.md

Pre-flight: Task 1 produces a discovery/provenance contract consumed by Task 2 extraction validation and Task 3 live pilot; current downloader exposes only URLs and current extractor requires an official-host PDF URL. Ruling: introduce a narrow reusable trust helper and carry the evidence through manifests and canonical source records; cost if wrong: a compatibility adjustment to an internal pipeline interface.

Pre-flight: Task 2 produces expanded manifest validation consumed by Task 3. Ruling: preserve legacy MEB-only manifest fields while requiring provenance evidence for any CDN target; cost if wrong: old generated manifests remain intentionally non-extractable until re-ingested.

Task 1: complete (commits 0c790e4..0c790e4, tests: python3 tests/source-ingestion/test_source_trust.py -v and python3 tests/source-ingestion/test_pipeline.py -v → 16/16 pass). Ruling: no commit was created because the Product Owner explicitly prohibited commit/push; cost if wrong: task boundaries are recorded only in this ledger and the working-tree diff.
Task 2: complete (commits 0c790e4..0c790e4, tests: npm run test:source → 23 Python tests and 3 API contract tests pass). Ruling: existing certificate manifests are preserved but extraction rejects them as incomplete provenance; cost if wrong: they need controlled re-ingestion before any future extraction attempt.
