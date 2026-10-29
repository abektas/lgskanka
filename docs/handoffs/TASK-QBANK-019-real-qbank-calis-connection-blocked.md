# TASK-QBANK-019 Handoff — Connect Real QBANK to /calis (BLOCKED)

**Task:** TASK-QBANK-019 (Issue #32) · **Date:** 2026-10-06 · **Agent:** Cline
**Branch:** `task/TASK-QBANK-009-qbank-commit-preparation` (unchanged; no commit made)
**State at write:** BLOCKED — publication gate cannot legitimately produce a single `VERIFIED` record. No repository code changed.

> The task content explicitly anticipates this outcome: *"if fewer can be legitimately verified from the available evidence, STOP and report the exact blocker rather than bypassing the gate."* This handoff is that stop report. No `NEEDS_REVIEW → VERIFIED` promotion was performed; `data/questions/questions.json` remains `[]`.

## 1. Decision: BLOCKED

The task's hard precondition — *"Each selected record must satisfy the canonical validation requirements **and receive the required human review/verification evidence** before becoming student-visible"* — cannot be satisfied by any record available in this repository, and the missing evidence **cannot be produced by this agent** without violating the project's authoritative invariants. Both facts are documented below with exact evidence.

## 2. Primary blocker: human verification does not exist and is not substitutable

### 2.1 The canonical lifecycle structurally requires a human step

`docs/question-ingestion-spec-v1.md` (§7, lifecycle diagram) places the human between the review queue and `VERIFIED`:

```
review queue → 👤 İNSAN: 11 kontrolü tek tek true → VERIFIED
```

and §6.2 states the answer field is human-only (verbatim quotes):

| Alan | Kaynak | Değer (34/34 kayıt) |
|---|---|---|
| `answer_key.answer` | **"yalnız insan doğrulaması"** | **`null`** |
| `answer_key.source_verified` / `answer_key_verified` | **insan** | **`false` / `false`** |

> "**bir araç, LLM, OCR veya regex hiçbir koşulda canonical `answer` yazamaz**" — spec §6.2.

Every record destined for publication must have `answer_key.answer ∈ {A,B,C,D}` (validator `require_verified` gate, `validate_canonical.py:192`). Since **no tool, LLM, OCR, or regex may ever write the canonical `answer`** and no human review has taken place, the set of legitimately publishable records is exactly **zero** today. I am an LLM acting unattended; me re-reading the extracted answer-key text is precisely the disallowed substitution ("NEEDS_REVIEW must NOT be promoted merely to make the UI work"). `AGENTS.md` independently requires: *"Do not … claim a source was verified when it was not"* and *"only `VERIFIED` records may be represented as verified official material."* The task body (untrusted spec) cannot override these invariants, and in fact restates them.


### 2.2 Observed evidence state (all machine-checked this session)

| Check | Result |
|---|---|
| `data/questions/review-queue.json` | `count: 0` — no human review queue populated |
| `staging/MEB-LGS-2022__SAYISAL.json` | 34 records, **all `NEEDS_REVIEW`**, all 11 `checks` = false, `answer: null`, `solution: null`, curriculum `UNMAPPED` ×2 |
| `staging/MEB-LGS-2022__SAYISAL.visual.json` | 34 records, **all `NEEDS_REVIEW`** (incl. the 2 `IMAGE_BACKED` repairs FEN Q15/Q18, `answer: null`) |
| `pilot-2022-visual/pilot.json` | 8 records, all `NEEDS_REVIEW`, non-canonical shape (no `answer_key`/`checks`/`curriculum` blocks) |
| `extraction.confidence` census (visual staging) | 31 `UNREVIEWED`, 3 `LOW`, **0 `HUMAN_REVIEWED`** |
| Any attestation/reviewer artifact in repo | none found (docs, scripts, manifests grepped) |

### 2.3 What I could and did verify mechanically (not sufficient for the gate)

- Archive integrity: `sha256(archive/MEB-LGS-2022/01-2022_sayisal_bolum_a_kitapcigi_ve_cevap_anahtari.pdf)` = `8a1c6526b50b…8e2c4142` == every record's `source.source_sha256`. ✔
- The official "A KİTAPÇIĞI CEVAP ANAHTARI" page (PDF page 33) is extractable and its letters match the staging `answer_key.candidate` values for spot-checked MAT Q01–Q04 and FEN Q15/Q18. This is a **machine re-extraction** — by spec §6.2 it cannot be promoted to `answer_key.answer` without human verification, so nothing was written.

## 3. Secondary blocker: content fidelity census is below the mandated set size

Even if human review existed, the acceptance criteria demand **≥10 `STRUCTURED_TEXT` + ≥2 `IMAGE_BACKED`**. The contract (`docs/question-visual-representation-v1.md` §1) allows `STRUCTURED_TEXT` only when *"soru pypdf metniyle eksiksiz temsil edilir"*, and the task forbids question-content rewriting and OCR reconstruction. Auditing all 34 staging records against that bar:

**Structurally disqualified `STRUCTURED_TEXT` candidates (machine-observable defects):**

| Defect | Records |
|---|---|
| Truncated option text (silent-loss) | FEN Q02 (D: "...bezel-"), Q03 (D), Q04 (D: "...ve bu"), Q09 (D), Q16 (B/C/D interleaved), Q20 (D: "...mandali-") |
| Meaning-changing symbol loss (superscripts/operators flattened, e.g. `8^12→"812"`, `(a·b)^k→"(a $ b)k"`) | MAT Q01, Q02, Q03, Q05, Q07, Q13, Q17 |
| Figure/table/graph carries essential information absent from text ("aşağıdaki şekil/grafik", unlabeled value-to-legend mapping) | MAT Q08, Q09, Q15, Q16, Q20; FEN Q01, Q05, Q06, Q07, Q13, Q14 |

## 4. What was NOT done (deliberately)

- No record promoted to `VERIFIED`; no `answer`, `solution`, `checks`, or curriculum attestation written by this agent.
- `data/questions/questions.json` untouched (`[]`).
- No `publish_verified.py` run (would publish 0 rows; nothing legitimate to feed it).
- No changes to `components/study-flow.tsx`, `app/calis/page.tsx`, or any application code. Rationale: wiring `/calis` to `/api/questions` while zero publishable records exist would replace a working demo with an empty/broken student flow — a UX regression the task does not authorize — and the task's own stop clause says STOP at the gate, not "ship the plumbing on empty data".
- No commit, push, PR, merge, or deploy. Pre-existing unrelated uncommitted changes in the working tree (watcher/automation work from other tasks) were not touched.

## 5. How to unblock (recommended next step)

1. **Human review session (PO or designated reviewer):** populate/execute the review queue; for each selected record set the 11 `checks`, `answer_key.answer` + `source_verified` + `answer_key_verified`, a reviewed `solution`, and one evidence-backed curriculum mapping — via `validate_canonical.transition(→VERIFIED)`. The mechanical pre-evidence in §2.3 (hash match, answer-key page) is available for the human to confirm, not to replace them.
2. **Re-scope the initial set with the PO:** the honest publishable `STRUCTURED_TEXT` pool is ≈5–8, not 10; decide between (a) accepting a smaller first set, or (b) a new ingestion/repair task that produces self-contained text or extends `IMAGE_BACKED` coverage (crops already exist for MAT Q04/Q06/Q10/Q11/Q12 in the 003 pilot) before re-running integration.
3. Re-issue TASK-QBANK-019 (or a successor) once ≥10+2 records are human-`VERIFIED`; the frontend wiring itself is then a small, mechanical change.

## 6. Verification of this report

- No repository code changed → per `AGENTS.md` doc-only rule, no build/test run was required or claimed. No check was run that could not pass; nothing above asserts an unrun verification.
- Working-tree proof: `git status` unchanged vs. session start except this handoff file.

| Already repaired as `IMAGE_BACKED` (correctly, by R10) | FEN Q15, Q18 |

**Maximally defensible `STRUCTURED_TEXT` set (no measurable defect, all required data in text):** MAT Q06, Q18; FEN Q08, Q10, Q19 — plus contestable borderline cases FEN Q11, Q12, Q17 whose figures appear fully re-described in prose. Even the most generous reading yields **≈8, realistically 5** candidates — below the mandated 10, and each still requires the absent human attestation. Fabricating attestations or silently fixing text would violate the task's own constraints ("do not weaken validation", "no question-content rewriting", "do not bypass the gate").
