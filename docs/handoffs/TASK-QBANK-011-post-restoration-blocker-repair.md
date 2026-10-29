# TASK-QBANK-011 Handoff — Post-Restoration Blocker Repair

**Task:** TASK-QBANK-011 (Issue #22) · **Date:** 2026-10-06 · **Agent:** Cline
**Branch:** `task/TASK-QBANK-009-qbank-commit-preparation`

> No secret/PII/student data was read or written. No commit/push/merge/rebase/reset/stash/clean/deploy/issue-close was performed.

## 1. Initial / final branch & working-tree state

- `git branch --show-current`: `task/TASK-QBANK-009-qbank-commit-preparation` (before and after).
- Tracked modified (13, before and after — QBANK-011 added no new tracked file):
  `app/api/questions/route.ts`, `app/globals.css`, `app/robots.ts`,
  `data/source-engine/config/source-registry.json`, `package.json`,
  `scripts/source-ingestion/canonical_schema.json`, `extract_pdf_candidates.py`,
  `publish_verified.py`, `validate_canonical.py`, `tests/source-ingestion/api-contract.test.mjs`,
  `tools/cline-watcher` (3 files).
- Untracked incl. QBANK-011 edits (marked ★): `.vscode/`, `app/pilot-2022/` ★,
  `app/pilot-2022-visual/`, `public/pilot-2022-visual/`,
  `scripts/.../pilot-2022-visual/`, `staging/MEB-LGS-2022__SAYISAL.visual.json`
  (unchanged), `render_visual_pilot.py`, `repair_structural_gate.py`,
  `docs/question-ingestion-spec-v1.md`, `docs/question-visual-representation-v1.md`,
  `tests/test_canonical_visual.py` ★, `test_visual_pilot.py`,
  `tests/test_visual_representation.py` ★, watcher notify files,

## 2. Files changed and why (3 files, smallest correct fix)

1. **`app/pilot-2022/page.tsx`** (untracked QBANK-002 file) — tsc/build blocker.
   Root cause: the page destructured `unparsed_question_numbers` from staging JSON.
   That key existed only in the contaminated 2026-10-04 worktree; the restored
   b425500 baseline has no such key → `TS2339` + knock-on `TS7006` on `row`.
   Fix: optional field with explicit `UnparsedRow` type; missing means "no
   recorded orphans", section renders (0). No data invented, consumer adapted
   to the verified source shape.
2. **`tests/source-ingestion/test_canonical_visual.py`** — 2 boundary failures.
   Raw record equality flagged all 34 records because repaired `.visual.json`
   carries contaminated `2026-10-04` `extraction.retrieved_at` while the restored
   original carries pristine `2026-10-01` stamps. Fix: normalize (drop) only
   that volatile field before comparison. Contract preserved: only R10 records
   differ structurally, others match exactly, no `visual`, `STRUCTURED_TEXT`.
3. **`tests/source-ingestion/test_visual_representation.py`** — 1 failure.
   Old assertion (both Q15+Q18 LOW + warnings) was calibrated to contamination
   (`option_value_empty` + LOW on Q15 was a QBANK-002/005-era mutation).
   Verified baseline: Q15 = `UNREVIEWED` + `[]`, Q18 = `LOW` +
   `['four_options_not_confidently_extracted']`. Fix asserts exact baseline
   provenance per record; integrity checks (NEEDS_REVIEW, answer null,
   VERIFIED blocked, options never fabricated) fully preserved.

## 3. Hash comparison (immutable, byte-identical)

- Original `MEB-LGS-2022__SAYISAL.json` worktree:
  `9c5691af7b475d0315515b62950f94441f133e02e3dcb35381045651b577cdd1`
  == `git show b425500:<file>` hash. Byte-identical, untouched by this task.
- Repaired `.visual.json`:
  `db79e5f9297e3ae64686d05b08477162f034957fe1e83676ae0db24b51f6212e`,

## 4. Test / build results (all green)

- `npx tsc --noEmit`: exit 0 (was 2 errors in `app/pilot-2022/page.tsx`).
- `python3 -m unittest discover -s tests/source-ingestion`: `Ran 127 … OK` (was 124 + 3 FAIL).
- `npm run test:source`: python 127/127 OK + node api-contract 8/8 pass.
- `npm run test:taxonomy`: 5/5 pass. `npm run test:ai`: 19/19 pass.
- `npm run validate:sources`: `OK: 6 official source records`.
- `npm run build`: success, 18 routes incl. `/pilot-2022`, `/pilot-2022-visual`.
- `git diff --check`: clean.

## 5. Remaining risks / blockers

1. Repaired `.visual.json` still carries contaminated `2026-10-04` timestamps on
   32 untouched records (tests normalize this field). Clean regeneration from
   the restored baseline via `repair_structural_gate.py` needs authorization —
   deliberately NOT done here.
2. QBANK-009 carry-overs apply (C1/C2 wording vs Issue 18, QBANK-007 authorship
   gap, concurrent-session risk). The base-branch `/_global-error` defect noted
   in QBANK-010 was not reached — build succeeds on this branch.
3. Watcher/notify files remain excluded from any QBANK commit.
4. No product/architecture decision made; Q15 recalibration is a verified-hash
   test correction, not a policy change.

## 6. Commit-readiness

All acceptance criteria pass: evidence byte-identical, visual separate/unchanged,
tsc/build green, 127 source + taxonomy + AI + API-contract + validate:sources
green, diff-check clean, no unrelated work lost. Safe for ChatGPT review.

READY FOR MANUAL COMMIT AUTHORIZATION: YES

  separate untracked artifact, byte-unchanged from QBANK-010.

  QBANK-009/010 handoffs, plus this report.
- `git diff --check`: clean. Pre-existing stash untouched.
