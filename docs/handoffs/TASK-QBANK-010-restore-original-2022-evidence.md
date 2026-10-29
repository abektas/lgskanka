# TASK-QBANK-010 Handoff — Restore Original 2022 Evidence

**Task:** TASK-QBANK-010 (Issue #21) · **Date:** 2026-10-06 · **Agent:** Cline
**Branch:** `task/TASK-QBANK-009-qbank-commit-preparation`

> No secret/PII/student data was read or written. No commit/push/merge/rebase/reset/stash/clean/deploy/issue-close was performed.

## 1. Branch & before/after state

| Check | Before restoration | After restoration |
|---|---|---|
| `git branch --show-current` | `task/TASK-QBANK-009-qbank-commit-preparation` | same branch (unchanged) |
| tracked modified | 14 incl. `staging/MEB-LGS-2022__SAYISAL.json` | 13 — staging original entry **gone** (matches HEAD) |
| untracked | 16 incl. `.visual.json` + QBANK-009 report | 16 + this report (visual untouched) |
| `git stash list` | pre-existing `stash@{0} "qbank-kalinti-issue10"` | untouched |
| `git diff --check` | clean | **clean** |

Preserved (post-restore `git status --short`): still modified (13):
`app/api/questions/route.ts`, `app/globals.css`, `app/robots.ts`,
`data/source-engine/config/source-registry.json`, `package.json`,
`scripts/source-ingestion/canonical_schema.json`, `extract_pdf_candidates.py`,
`publish_verified.py`, `validate_canonical.py`, `tests/source-ingestion/api-contract.test.mjs`,
`tools/cline-watcher/{lib/config.mjs, systemd/cline-task-watcher.service, watcher.mjs}`.
Still untracked: `.vscode/`, `app/pilot-2022/`, `app/pilot-2022-visual/`,
`public/pilot-2022-visual/`, `scripts/.../pilot-2022-visual/`,
`staging/MEB-LGS-2022__SAYISAL.visual.json`, `render_visual_pilot.py`,
`repair_structural_gate.py`, `docs/question-ingestion-spec-v1.md`,
`docs/question-visual-representation-v1.md`,
`tests/{test_canonical_visual,test_visual_pilot,test_visual_representation}.py`,
`tools/cline-watcher/{lib/notify.mjs, test/notify.test.mjs}`,
`docs/handoffs/TASK-QBANK-009-qbank-commit-preparation.md`.
Only delta: the staging original no longer differs from HEAD.

## 2. Baseline ref — how identified

- `git log --follow --oneline -- staging/MEB-LGS-2022__SAYISAL.json` returns exactly one
  commit: `4dac261 feat(source-engine): harden ingestion, quarantine bad artifact, subject-aware answer key`.
- `git rev-parse 4dac261:<file>` == `git rev-parse HEAD:<file>` ==
  blob `4ccbcd452623614196aa60a19bdee34be96197dd`.
- `git merge-base --is-ancestor 4dac261 HEAD` is true; intervening commits touch only
  automation/review files, never the staging file.
- **Baseline: `HEAD` = `b425500a170ef7ca89fd4a2578b438919d094d7d`,
  blob `4ccbcd452623614196aa60a19bdee34be96197dd` (= `4dac261` blob).**
  The QBANK-002 regeneration (`2026-10-04T07:07:05Z`, `unparsed_question_numbers`,
  `option_value_empty` on FEN:Q15) existed only as uncommitted worktree mutation.

## 3. Restoration method (surgical, single file, worktree-only)

No `git reset/restore/checkout <broad path>`, no stash/clean, no index change:

```sh
git show HEAD:scripts/source-ingestion/data/questions/staging/MEB-LGS-2022__SAYISAL.json > /tmp/qbank010_baseline_original.json
cp /tmp/qbank010_baseline_original.json scripts/source-ingestion/data/questions/staging/MEB-LGS-2022__SAYISAL.json
```

## 4. Hashes & exact comparison

| Artifact | Before (sha256) | After (sha256) |
|---|---|---|
| `MEB-LGS-2022__SAYISAL.json` worktree | `dd8fec58e813a63b45ed7a31a8f88bd5012b48741e60b811e41555ae59020348` (contaminated) | `9c5691af7b475d0315515b62950f94441f133e02e3dcb35381045651b577cdd1` |
| Baseline `git show HEAD:<file>` | `9c5691af7b475d0315515b62950f94441f133e02e3dcb35381045651b577cdd1` | identical |
| `.visual.json` (untracked repaired) | `db79e5f9297e3ae64686d05b08477162f034957fe1e83676ae0db24b51f6212e` | same value UNCHANGED |

- `git diff --quiet HEAD -- <original>` = IDENTICAL-TO-BASELINE (empty diff).
- `git hash-object` worktree file = `4ccbcd452623614196aa60a19bdee34be96197dd` = HEAD blob.
- Contamination removed: `retrieved_at 2026-10-04T07:07:05Z` restored to `2026-10-01T20:26:24Z`;
  top-level `unparsed_question_numbers` removed; `review_reasons` back to single entry;
  FEN:Q15 back to UNREVIEWED with empty warnings.

## 5. Original vs repaired artifact

- Original (restored): NEEDS_REVIEW, published=false, 34 records, no visual keys,
  no `unparsed_question_numbers`. Tracked-HEAD file, now clean in worktree.
- Repaired `.visual.json`: NEEDS_REVIEW, published=false, 34 records,
  `visual_backed_record_count=2`, FEN:Q15/Q18 null stem/options with IMAGE_BACKED visual
  blocks bound to official PDF crops. Byte-identical before/after; never staged.
- Boundary holds: text evidence in original; visual-only evidence only in `.visual.json`
  plus `public/pilot-2022-visual/` crops. No merge.

## 6. Q15/Q18 lifecycle (restored original)

- MAT Q15: answer=null (candidate B), verifications false, NEEDS_REVIEW, UNREVIEWED/[] — NO fabrication.
- MAT Q18: answer=null (candidate A), verifications false, NEEDS_REVIEW, UNREVIEWED/[] — NO fabrication.
- FEN Q15: answer=null (candidate A), verifications false, NEEDS_REVIEW, UNREVIEWED/[] with D empty — NO fabrication.
- FEN Q18: answer=null (candidate D), verifications false, NEEDS_REVIEW,
  LOW with `four_options_not_confidently_extracted`, options empty — NO fabrication.
- Top-level: status=NEEDS_REVIEW, published=false. Nothing verified or published.

## 7. Tests and results

- `git diff --check`: clean.
- `npm run test:taxonomy`: 5/5 pass.
- `npm run test:ai`: 19/19 pass.
- `npm run validate:sources`: OK, 6 official source records.
- `npm run test:watcher`: 43/43 pass.
- `api-contract.test.mjs`: 8/8 pass.
- `R9CanonicalVisualTest` (repaired artifact, 10 tests): 10/10 pass.
- `npm run test:source` (127 tests): 124 pass, 3 FAIL — all three are boundary
  expectations written against the contaminated worktree (see below); all else green.
- `npx tsc --noEmit`: 2 errors, both in `app/pilot-2022/page.tsx`
  (`unparsed_question_numbers` missing on restored type; implicit-any `row` param).
- `npm run build`: fails at TypeScript stage on the same pilot page error
  (the QBANK-009 `/_global-error` prerender defect was not reached).

### Why the 3 test:source failures are expected (not a regression)

1. `test_repair_changes_only_the_broken_records` — expects changed(original to
   repaired) to equal only FEN:Q15/FEN:Q18; now 34 records differ because repaired
   carries contaminated `2026-10-04` timestamps while original is pristine again.
2. `test_structurally_complete_records_are_left_untouched` — same timestamp cause.
3. `test_failing_records_are_flagged_low_confidence_and_never_verified` (FEN:Q15) —
   expects non-empty warnings plus LOW; restored baseline is UNREVIEWED with empty
   warnings (the `option_value_empty` flag was QBANK-002/005-era mutation, not baseline).
   These tests calibrated to the contamination and need a PO/ChatGPT recalibration or
   regeneration decision. No test file was modified in this task.

### New tsc/build blocker caused by the restoration (must-fix before commit)

`app/pilot-2022/page.tsx` (QBANK-002 worktree file) destructures
`unparsed_question_numbers` from the staging JSON. That key existed only in the
contaminated worktree version; the pristine baseline has no such key, so tsc and build
now fail. Fix direction is a product decision (optional field, feed page from repaired
artifact, or drop the section), so no code was changed here.

## 8. Remaining risks and blockers

1. BLOCKING: pilot page type error; tsc and build fail. Needs PO/ChatGPT fix decision.
2. BLOCKING: 3 test:source boundary tests red (calibrated to contamination).
   Needs recalibration or regeneration decision; assertions must not be silently weakened.
3. PENDING: repaired `.visual.json` still carries contaminated `2026-10-04` timestamps on
   its 32 untouched records. Cleanest path is regenerating it from the restored baseline
   via `repair_structural_gate.py`, but that rewrites the repaired artifact and needs
   authorization, so it was deliberately NOT done here.
4. PENDING: QBANK-009 open items carry over (C1/C2 wording vs Issue 18, QBANK-007
   authorship gap, pre-existing base-branch `/_global-error` build defect,
   concurrent-session risk). Re-run `git status` before any staging.
5. Watcher/notify files remain correctly excluded from any QBANK commit.

## 9. Git safety status

Dedicated branch held; 0 staged; 0 commits; no push/merge/rebase/reset/stash/clean/
revert/force/history-rewrite/deploy/issue-close. Pre-existing stash untouched.
Prohibited operations: NONE performed.

## 10. Final safety status

Original 2022 evidence exactly matches the verified pre-QBANK-002 baseline (hash, blob,
empty diff) and the repaired `.visual.json` remains separate and byte-unchanged. But tsc,
build, and 3 boundary tests are red as a direct consequence, so commit authorization is
NOT safe yet. Remaining work is a small decided fix (pilot page plus test
recalibration/regeneration), not new provenance damage.

READY FOR MANUAL COMMIT AUTHORIZATION: NO
