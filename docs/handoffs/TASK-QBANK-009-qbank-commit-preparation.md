# TASK-QBANK-009 Handoff — QBANK Branch & Commit Preparation

**Task:** TASK-QBANK-009 (Issue #20) · **Date:** 2026-10-06 · **Agent:** Cline
**Status:** READY FOR MANUAL COMMIT AUTHORIZATION: YES

> **Concurrency note:** a *second* Cline/IDE session edited this file at 00:18–00:25 (+0300) and left
> hung `git diff` processes (pids 17905/17914/17917, started 00:14). This version supersedes that
> draft; material corrections vs it are listed in §10. No secret/PII/student data was read or written.

## 1. Branch & upstream state

| Property | Value |
|---|---|
| Branch | `task/TASK-QBANK-009-qbank-commit-preparation` — CREATED via `git switch -c` (working tree preserved) |
| Base | `feature/faz1-gemini-pr-review` @ `b425500`; `origin/feature/faz1-gemini-pr-review` @ `b425500` (0 ahead / 0 behind at creation) |
| `main` | behind `origin/main` by 4 (unchanged, untouched) |
| Stash | pre-existing `stash@{0} "qbank-kalinti-issue10"` — NOT touched |
| Commits/push/merge/rebase/reset/stash/clean/deploy/issue-close | **NONE performed** |

## 2. Working-tree inventory (30 entries, all classified)

**Modified tracked (14):** `app/api/questions/route.ts` (+46/−4) · `app/globals.css` (+23) ·
`app/robots.ts` (+3/−1) · `data/source-engine/config/source-registry.json` (+1/−1) · `package.json` (+1/−1) ·
`scripts/source-ingestion/canonical_schema.json` (+2/−2) · `staging/MEB-LGS-2022__SAYISAL.json` (+72/−37) ·
`extract_pdf_candidates.py` (+26) · `publish_verified.py` (+10/−1) · `validate_canonical.py` (+132/−4) ·
`tests/source-ingestion/api-contract.test.mjs` (+57) · `tools/cline-watcher/{lib/config.mjs,systemd/…service,watcher.mjs}` (+46).

**Untracked (16):** `app/pilot-2022/` · `app/pilot-2022-visual/` · `public/pilot-2022-visual/` (8 `mat-*` + 2 `img-*` PNG) ·
`scripts/…/pilot-2022-visual/` · `scripts/…/staging/MEB-LGS-2022__SAYISAL.visual.json` · `render_visual_pilot.py` ·
`repair_structural_gate.py` · `docs/question-ingestion-spec-v1.md` · `docs/question-visual-representation-v1.md` ·
`tests/{test_canonical_visual,test_visual_pilot,test_visual_representation}.py` ·
`tools/cline-watcher/lib/notify.mjs` · `tools/cline-watcher/test/notify.test.mjs` · `.vscode/` (IDE, unrelated) ·
`docs/handoffs/TASK-QBANK-009-qbank-commit-preparation.md` (this report).

## 3. Provenance classification (evidence: in-file task labels + watcher stream logs + artifact timestamps)

| Group | Files |
|---|---|
| **QBANK-002** | `source-registry.json` (URL slug `sinavla`→`sinavin`, 90 log hits in 002 log) · `extract_pdf_candidates.py` hunks @16/@302/@349/@371/@417 (`ORPHAN_NUMBER`+`unparsed_question_numbers` — designed in 002's log; extraction ran `2026-10-04T07:07:05Z`, inside 002's window 06:44–07:12Z) · staging JSON timestamp hunks + `@7526` (`unparsed_question_numbers` + `question_numbers_without_text_block`) · `app/pilot-2022/` (eyebrow `TASK-QBANK-002`) |
| **QBANK-003** | `app/globals.css` (`.pv-*` block) · `app/pilot-2022-visual/` · `public/pilot-2022-visual/mat-*.png` (8) · `scripts/…/pilot-2022-visual/` · `render_visual_pilot.py` · `test_visual_pilot.py` (all carry `TASK-QBANK-003` labels; present in 003's log) |
| **QBANK-004** | `docs/question-ingestion-spec-v1.md` (header `Görev: TASK-QBANK-004`; authored in 004's run) |
| **QBANK-005** | `app/api/questions/route.ts` (whole — 2 hunks, R9 gate; no 007 markers) · `canonical_schema.json` (whole — `representation`/`visual`/`$defs` **and `allOf`**: `allOf`+`if/then` designed in 005's log, so this is **not** mixed) · `validate_canonical.py` (whole — single hunk; `validate_structure`/`validate_visual` are 005's) · `publish_verified.py` · `extract_pdf_candidates.py` hunk @91 (`option_value_empty` — invented in 005's log; 005 observed Q15 still `warnings: []` on 10-05, so this line was added by 005's targeted edit) · staging JSON hunk `@6284` confidence+warnings lines (FEN:Q15) · `.visual.json` · `repair_structural_gate.py` · `test_canonical_visual.py` · `test_visual_representation.py` · `api-contract.test.mjs` · `public/…/img-q15-p28.png`, `img-q18-p30.png` · `docs/question-visual-representation-v1.md` (§1–7) · spec doc additions (line 11 note, `Ek II`) |
| **QBANK-007** | `app/robots.ts` (C5 comment+disallow) · `docs/question-visual-representation-v1.md` §8 · `test_visual_representation.py` line 136 (C4 comment) — **only 3 literal `TASK-QBANK-007` markers exist in the tree**; no watcher log contains them (007's and 008's watcher runs failed at iteration 1, 0 tokens) ⇒ authored in an **unlogged/manual session** (self-labelled provenance — see §10) |
| **Watcher/Notify (OUT)** | `tools/cline-watcher/lib/config.mjs`, `systemd/cline-task-watcher.service`, `watcher.mjs`, `lib/notify.mjs`, `test/notify.test.mjs`, **`package.json`** (only semantic change = `notify.test.mjs` added to `test:watcher`, verified by JSON diff) |
| **Unrelated (OUT)** | `.vscode/` (IDE metadata) · pre-existing stash · `SUBJECT_HEADERS` fix (**absent** from tree ✓) · PD-1/PD-6 (documented only, no code) |

## 4. Mixed-provenance files — exact hunk map

1. **`extract_pdf_candidates.py` — MIXED 002/005 — separable at hunk level (default `git add -p`):**
   `@@ -16` → G1 · `@@ -91` (option_value_empty) → G4 · `@@ -302`, `@@ -349`, `@@ -371`, `@@ -417` → G1.
2. **`staging/MEB-LGS-2022__SAYISAL.json` — MIXED 002/005 — separable, one line-level carve-out:**
   34 timestamp-only hunks + `@@ -7526` → G1. Hunk **`@@ -6284,9 +6284,11`** (FEN:Q15 extraction block) mixes tasks:
   keep ONLY the `retrieved_at` line for G1; the `confidence: LOW` + `warnings: ["option_value_empty"]` lines → G4.
   Method: `git add -p` → `e` (edit) on that hunk, or `git apply --cached -U0` with a 1-line patch for G1 and a 2-line patch for G4.
   **Result after G1 = faithful 002-era output (Q15 still `warnings: []`); G4 adds 005's correction. Deterministic.**
3. **`app/api/questions/route.ts` — NOT mixed** (whole → G4). **`canonical_schema.json` — NOT mixed** (whole → G4;
   `allOf` = C4 content but authored inside 005's session — cannot and need not be split). **`validate_canonical.py` — NOT mixed** (whole → G4).
4. **Untracked files cannot be hunk-staged** (whole-file units). Mixed new files, flagged **not guessed**:
   - `docs/question-visual-representation-v1.md` = 005 (§1–7) + 007 (§8). Options: **(a)** commit whole in G4 with §8 riding, or
     **(b)** two-step: G4 without §8, G5 adds §8 (exact content = lines 93–108 of the file).
   - `docs/question-ingestion-spec-v1.md` = 004 + 005 notes (line 11, `Ek II`, related 10-05 lines). Options: whole → G3 with 005 notes riding, or two-step (G3 base / G4 adds 005 notes).
   - `test_visual_representation.py` = 005 + 007 C4 comment (line 136) → whole → G4 (comment rides) or two-step.
   Recommend (b) only if ChatGPT wants strict label purity; (a) is commit-order-safe and simpler. **PO/ChatGPT choice → §10.**
5. **`public/pilot-2022-visual/` — mixed by FILE:** `mat-*` (8) → G2; `img-*` (2) → G4 (C3 record: prefixes encode provenance).

## 5. C1–C5 / R9–R10 verification

| Item | Status | Evidence |
|---|---|---|
| **C1, C2** | **NOT VERIFIED** | Issue #18/#19 bodies are not retrievable (GitHub returns 404 anonymously; `gh` absent; no local snapshot — only issue #3 exists). No repo file defines C1/C2. Interpretation (issue title “Commit Boundary…”): C1 = QBANK work isolated from PR #6 branch → holds (dedicated branch, base = PR #6 tip, no commits); C2 = mixed files hunk-separated → holds per §4. Exact wording needs ChatGPT confirmation. |
| **C3 — asset boundary** | **VERIFIED** | §8 record: `mat-*` (003) and `img-*` (005) coexist in `public/pilot-2022-visual/`, referenced by `pilot.json` / `.visual.json` respectively; no files moved; both sets exist on disk (10/10). |
| **C4 — schema hardening** | **VERIFIED** | `canonical_schema.json` `question.allOf` has exactly two `if/then` branches (IMAGE_BACKED/HYBRID ⇒ `visual` required); no reverse rule; regression test `test_schema_declares_representation_and_visual_provenance` present & passing. (C4 content authored in 005's session; 007 recorded the decision.) |
| **C5 — pilot publish risk** | **VERIFIED** | `app/robots.ts` disallow = `[/api/, /profil, /pilot-2022, /pilot-2022-visual]`; both pilot pages carry `robots: {index:false, follow:false}`; `app/sitemap.ts` has **no** pilot entries; no nav links in `components/`. |
| **R9 — canonical visual representation** | **VERIFIED** | `test_canonical_visual.py::R9CanonicalVisualTest`, `test_visual_representation.py::VisualRepresentationTest`, `api-contract.test.mjs` 8/8 — all pass in my runs (§7). |
| **R10 — structural gate** | **VERIFIED** | Real artifact: original Q15 fails `present but empty: D`, Q18 fails `missing A-D keys`; `test_visual_representation.py::RealArtifactTest` + `test_canonical_visual.py` gate tests pass; repair script emits `IMAGE_BACKED` without inventing options/answers. |

## 6. Original vs repaired 2022 artifacts

| Artifact | State | Result |
|---|---|---|
| **Original** `staging/MEB-LGS-2022__SAYISAL.json` (tracked, modified) | 34 records; Q15 `D:""` and Q18 `options:{}` **defects preserved**; `representation` absent; `status: NEEDS_REVIEW`; top-level `published: false`; carries 002-era `retrieved_at 2026-10-04T07:07:05Z`, `unparsed_question_numbers` (6) and 005's `option_value_empty` warning on Q15 | **VERIFIED — still red under R10, still unpublished** |
| **Repaired** `staging/MEB-LGS-2022__SAYISAL.visual.json` (untracked) | Separate file; only Q15/Q18 changed: `stem/options: null`, `representation: IMAGE_BACKED`, `visual` provenance (img-*, page 28/30, SHA-256, `reconstructed_from_ocr:false`); `answer: null`; `NEEDS_REVIEW`; `published: false` | **VERIFIED — separate file, lifecycle unchanged, passes repaired-gate tests** |
| Difference vs `HEAD` original | Regeneration (timestamps + orphan block) mutated the tracked original in place — the **QBANK-006 caveat** | Decision required → §10 |

## 7. Test commands & results (run by THIS session, 2026-10-06 00:26–00:31 +0300)

| Command | Result |
|---|---|
| `npm run test:source` | **PASS** — `Ran 127 tests` (python: incl. `test_canonical_visual`, `test_visual_representation`, `test_visual_pilot`) + node `tests 8 / pass 8` (api-contract incl. R9), exit 0 |
| `npm run test:taxonomy` | **PASS** — exit 0, 0 todo/fail |
| `npm run test:ai` | **PASS** — 19/19 smoke tests, exit 0 |
| `npx tsc --noEmit` | **PASS** — exit 0 |
| `npm run validate:sources` | **PASS** — `OK: 6 official source records`, exit 0 |
| `git diff --check` | **PASS** — exit 0, no whitespace errors |
| `npm run build` | **FAIL — but PRE-EXISTING, not a QBANK regression (isolated).** Main tree fails exporting framework page `/_global-error`: `TypeError: Cannot read properties of null (reading 'useContext')` (compile OK); reproduced twice (00:29, 00:38), so not concurrent-build interference. **Clean-HEAD isolation build** (detached `b425500` worktree, hardlinked `node_modules`, `/tmp/qb009-wt3.log`) **failed identically by 00:39** ⇒ the failure exists on the base commit without any working-tree changes. Same error also appears in QBANK-005's Oct-5 session log. |

## 8. Exact proposed commit groups (ordered; no commits made)

All groups are staged from the *current* working tree; nothing is committed until manual authorization.

| # | Message (proposal) | Files / hunk scope |
|---|---|---|
| **G1** | `feat(qbank): QBANK-002 — 2022 MEB source pilot + silent loss detection` | `data/source-engine/config/source-registry.json` · `extract_pdf_candidates.py` hunks @16,@302,@349,@371,@417 · staging JSON: all 34 `retrieved_at` hunks + `@7526` + the **single `retrieved_at` line** inside `@6284` · `app/pilot-2022/**` |
| **G2** | `feat(qbank): QBANK-003 — 2022 visual pilot (crops + review surfaces)` | `app/globals.css` · `app/pilot-2022-visual/**` · `public/pilot-2022-visual/mat-*.png` (8) · `scripts/source-ingestion/data/questions/pilot-2022-visual/**` · `render_visual_pilot.py` · `tests/source-ingestion/test_visual_pilot.py` |
| **G3** | `docs(qbank): QBANK-004 — question ingestion spec v1` | `docs/question-ingestion-spec-v1.md` (whole; 005 notes ride per §4.4 option (a), or two-step per option (b)) |
| **G4** | `feat(qbank): QBANK-005 — canonical visual representation (R9) + structural gate (R10)` | `app/api/questions/route.ts` (whole) · `canonical_schema.json` (whole) · `validate_canonical.py` (whole) · `publish_verified.py` · `extract_pdf_candidates.py` hunk @91 · staging JSON `confidence`+`warnings` lines of `@6284` · `.visual.json` · `repair_structural_gate.py` · `test_canonical_visual.py` · `test_visual_representation.py` · `api-contract.test.mjs` · `public/pilot-2022-visual/img-q15-p28.png`, `img-q18-p30.png` · `docs/question-visual-representation-v1.md` (§8 excluded if option (b)) |
| **G5** | `feat(qbank): QBANK-007 — commit boundary decisions C3–C5 record` | `app/robots.ts` · plus §8 of the visual doc / C4 comment in the test file / spec 005-notes **only if** option (b) two-step was chosen for the respective file; otherwise robots.ts alone (see §4.4) |
| **OUT-1** | watcher/notify (NOT QBANK) | `tools/cline-watcher/lib/config.mjs`, `systemd/cline-task-watcher.service`, `watcher.mjs`, `lib/notify.mjs`, `test/notify.test.mjs`, `package.json` — recommended on an AUTOMATION branch, per §9 |
| **OUT-2** | unrelated | `.vscode/` — exclude/ignore |
| **G0/G6** | this handoff | `docs/handoffs/TASK-QBANK-009-qbank-commit-preparation.md` — commit last (or with G5) at ChatGPT's discretion |

**Staging mechanics for G1/G4 (deterministic):** `git add` the whole-file groups first; for the two mixed files use
`git add -p` hunk selection (extract: straightforward; staging JSON `@6284`: edit mode keeping only the `retrieved_at`
line for G1), **or** build `-U0` patches. Order G1 → G4 for the staging file. After G4 the index equals the working tree;
no file content is ever rewritten by this plan.

## 9. Watcher/notify out-of-band group

Excluded from every QBANK commit (verified: their only content is desktop-notify wiring — `desktopNotify` config,
`notify-send` invocation in `watcher.mjs`, systemd `Environment=` lines, `notify.mjs` + its test, and the single
`test:watcher` script addition in `package.json`). Recommended home: a `task/TASK-AUTOMATION-*` branch + separate PR.

## 10. Unresolved risks / decisions (must be read before authorization)

1. **`npm run build` fails on `/_global-error` prerender — ISOLATED AS PRE-EXISTING** (clean `b425500` fails identically;
   reproduced in main tree twice; same error in QBANK-005's Oct-5 log). **Does not block commit authorization.** It DOES block
   a green merge gate: the base branch itself does not build in this environment (Next 16 `/_global-error` export). Flagged for
   ChatGPT/Product Owner as a pre-existing base-branch defect — no fix attempted here (out of scope, no task invented).
2. **PENDING (PO/ChatGPT decision) — original staging artifact mutated in place** (QBANK-006 caveat): timestamps/orphan block
   differ from `HEAD`. Options: **(i)** accept as QBANK-002's legitimate regeneration, documented here (plan in §8 assumes this);
   **(ii)** restore pristine `HEAD` original first, then treat 002's regeneration as its own commit anyway (same hunk plan);
   **(iii)** drop 002's regeneration entirely (would contradict 002/003 evidence — not recommended). Not decided here.
3. **PENDING — C1/C2 exact wording** unverifiable locally (issue #18 404); confirm against Issue #18 text at review.
4. **PENDING — QBANK-007 authorship gap:** 007's watcher run failed (0 tokens); its 3 labelled edits exist only via an
   unlogged session (likely manual Cline/Codex per AGENTS.md). Provenance is self-labelled; ChatGPT should confirm.
5. **PENDING — QBANK-003 finishText claims it regenerated the staging baseline**, but artifact timestamps (`07:07:05Z`) fall
   inside QBANK-002's run and 003's log contains no own extraction output → assigned to G1 on artifact evidence; flagged, not guessed.
6. **PENDING — §4.4 two-step vs ride-along choice** for the three mixed *new* files (product/review preference; both deterministic).
7. **Concurrent session** may still write to this tree (hung `git diff` pids; `.vscode` at 00:18; this file rewritten 00:24/00:25).
   Re-run `git status` before staging; do not authorize commits while another agent is active.
8. **Corrects the concurrent draft** (material): `package.json` is watcher-only (not “QBANK-006 test”); `route.ts` is single-task
   005 and was **missing from its commit groups**; `app/pilot-2022/` = 002 (it listed it under 003); registry URL direction is
   `sinavla`→`sinavin`; `canonical_schema` hunk 2 is `$defs/visual` (005), not C4 — `allOf` sits in hunk 1; `validate_canonical`
   has one hunk and no 007 content; staging “orphan per-record warnings” do not exist (real additions: `unparsed_question_numbers`
   + review reason); its test results were not run by us — §7 supersedes.

## 11. Final Git safety status

`git status`: dedicated branch checked out; 14 modified + 16 untracked, **0 staged, 0 commits** · no push/merge/rebase/reset/
stash/clean/revert/force/history rewrite/deploy/issue-close · stash@{0} untouched · no secrets/PII/student data in diff or report ·
`git diff --check` clean · isolation worktrees used for the clean-HEAD build were removed after the run (`git worktree list` shows
only this worktree + the pre-existing `greeting-in-turkish`); build logs kept at `/tmp/qb009-*.log` · tree recoverable.

**READY FOR MANUAL COMMIT AUTHORIZATION: YES**
