# AGENTS.md — LGS AI Coach project contract

This file is the durable working agreement for everyone contributing to this project. Follow it alongside the user's current request. The user is the Product Owner and has final say on priorities and product behavior.

## Roles and collaboration

- **User — Product Owner:** Sets goals, priorities, and product decisions.
- **ChatGPT — Architect, Planner, Reviewer:** Clarifies requirements, designs architecture/data rules, plans changes, checks source and product policy, and reviews implementation.
- **Codex — Implementer, Tester, Git Operator:** Inspects the repository, implements the approved scope, runs relevant checks, reports diffs/results, and performs Git operations when requested or clearly needed.
- Keep the user out of routine message-passing between ChatGPT and Codex. Use this file and project artifacts as the shared source of technical truth. Record durable decisions here or in an appropriate project document.

## Project scope and product invariants

- This is an **LGS** learning product. Exam content scope starts in **2018**. Exclude TEOG and all pre-2018 exam questions/content from the LGS question bank and LGS performance claims. Clearly label any contextual historical material that is intentionally retained outside the question bank.
- Preserve the existing UI, user flows, and architecture unless a planned change explicitly calls for changing them. Prefer small, reversible changes that fit the current app.
- Avoid broad refactors, framework swaps, wholesale file replacement, and unrequested redesigns. Inspect the relevant code and preserve working behavior.
- Keep student-facing language supportive, clear, age-appropriate, and non-shaming. Explain errors as learnable skill gaps, not fixed ability.

## Curriculum layers

Maintain two distinct curriculum layers; never silently merge or conflate them:

1. `LGS_REFERENCE_2018_PLUS`: stable exam-reference curriculum aligned to LGS questions from 2018 onward. Use this layer for historical exam classification and longitudinal comparisons.
2. `CURRENT_TYMM`: the currently effective Türkiye Yüzyılı Maarif Modeli curriculum, with its own effective dates, outcomes, and source evidence. Use it for current instructional planning.

Every curriculum mapping must identify its layer, version/effective period, and supporting source. When mappings differ, preserve both and explain the difference rather than overwriting one with the other.

## Source policy and provenance

Use this source hierarchy for curriculum, exam, and official policy claims:

1. Official MEB sources: current curriculum documents, official guides, announcements, and publications.
2. ÖDSGM / official Ministry assessment and evaluation materials, including official LGS questions and answer keys.
3. Other official public institutions when directly relevant.
4. Secondary sources only as discovery/context; they cannot establish an official curriculum or answer-key fact when an authoritative source is available.

Record provenance for every imported or verified record: source title/type, issuing organization, canonical URL or repository locator, publication/exam year, retrieval date, applicable curriculum layer/version, and verification status. Preserve source attribution and any usage/licensing restrictions. Do not invent sources or claim a source was verified when it was not.

Use explicit source types such as `OFFICIAL_CURRICULUM`, `OFFICIAL_EXAM_QUESTION`, `OFFICIAL_ANSWER_KEY`, `OFFICIAL_GUIDE`, `OFFICIAL_ANNOUNCEMENT`, and `SECONDARY_REFERENCE`. Use explicit statuses such as `DISCOVERED`, `IMPORTED_UNVERIFIED`, `VERIFIED`, `REJECTED`, and `NEEDS_REVIEW`; only `VERIFIED` records may be represented as verified official material. Retain a reason and reviewer/date for rejection or manual verification where feasible.

### Ingestion, identity, and manifests

- Keep original source files immutable. Store normalized/derived data separately and preserve a link to the original.
- Compute a cryptographic content hash (prefer SHA-256) for each ingested source file and record it in an ingestion manifest with source identity, retrieval/import time, parser/version, and resulting record IDs/counts.
- Make ingestion idempotent: use stable source identifiers and hashes to avoid duplicate records; detect changed content and reprocess it deliberately rather than silently overwriting reviewed data.
- Keep imports auditable and reversible. Record validation failures and skipped items; never hide partial ingestion or silently drop provenance.

## Question bank and answer integrity

- A question may be called **MEB/official/verified** only when its official origin and exact source are recorded and independently checked against the source. AI-generated or adapted questions must never claim to be MEB questions.
- Give AI-generated/adapted questions an explicit provenance label (for example `AI_GENERATED` or `ADAPTED`) and keep them distinct from official questions in storage, UI, analytics, and exports.
- Do not publish a question as usable until required fields, curriculum mapping, answer, explanation, source/provenance, and validation status are present. Mark uncertain records `NEEDS_REVIEW` and keep them out of verified practice flows.
- Answer keys and canonical correct answers are server-side data. Never ship authoritative answer keys in client bundles, HTML, public static files, or client-readable API payloads before submission. The server evaluates answers and returns only what the current flow needs.
- Validate question format, options, single/multiple-answer rules, answer existence, explanation consistency, duplicate identity, source alignment, and curriculum alignment. Keep a review path for ambiguous or disputed items.

## Error taxonomy: H1–H7

Use the established first-error taxonomy consistently in analysis, feedback, analytics, and spaced repetition:

- **H1 — Concept/knowledge gap:** the required concept, rule, or fact is not known or understood.
- **H2 — Misconception:** a known idea is applied through an incorrect mental model.
- **H3 — Reading/interpretation:** the prompt, data, condition, or requested output is misunderstood.
- **H4 — Strategy/method selection:** an unsuitable approach is selected or the problem is not decomposed effectively.
- **H5 — Procedure/calculation:** the selected method is appropriate but an execution, operation, or calculation step is wrong.
- **H6 — Attention/working discipline:** a preventable omission, sign/unit/marking slip, or loss of focus causes the error.
- **H7 — Time/exam management:** time allocation, pacing, or pressure management prevents a correct solution.

Classify the earliest causal error (“first error”), not merely the final wrong answer. Allow evidence-based uncertainty and review; do not force a confident label from insufficient evidence. If project data currently defines a more specific canonical wording for these codes, preserve that wording and update this section deliberately rather than changing code meanings silently.

## Learning loop and assessment

- Spaced repetition should schedule review from demonstrated mastery, recency, and error type, with a way to correct or dismiss a mistaken diagnosis. Avoid presenting a heuristic schedule as scientifically precise.
- Adaptive weekly tests should use curriculum coverage, learner performance, and difficulty balance. Keep their selection logic explainable and auditable.
- Five-week mock exams should approximate the applicable LGS structure and timing using appropriately sourced/labelled material. Do not imply a generated mock is an official exam.
- Keep learning recommendations actionable and connected to the diagnosed skill/outcome. Do not treat a single answer as a stable judgement about a student.

## AI providers and secret handling

- Follow the existing provider abstraction and documented environment configuration (including Gemini, OpenRouter, and local providers) unless a planned architectural change is approved.
- API keys, tokens, credentials, and private provider URLs belong only in local environment/configuration or a managed secret store. Never expose them in source, logs, browser code, screenshots, error messages, documentation examples, Git history, or client responses.
- Keep `.env.local` and equivalent secrets out of Git. `.env.example` may contain variable names and safe placeholders only.
- Make provider/model identity explicit where useful, handle provider failure safely, validate AI output server-side, and do not treat generated output as verified source material.
- Minimize data sent to external AI providers; disclose the relevant processing in the product and do not send unnecessary identifiers or student personal data.

## Privacy, student safety, and KVKK

- Collect only data needed for learning functionality. Avoid collecting direct identifiers; do not place student PII, voice, photos, credentials, or private learning records in Git, fixtures, logs, analytics, screenshots, or issue descriptions.
- Voice recordings and uploaded solution photos are temporary inputs. Delete the raw voice/photo permanently after analysis completes (including failure/timeout cleanup); persist only the minimum derived learning data needed for the requested feature. Do not retain raw media for debugging or model improvement by default.
- Explain what is processed, why, where it is sent, and how long derived information is kept in age-appropriate, understandable language. Provide appropriate consent/guardian and deletion controls for the intended age group and deployment context.
- Apply data minimization, purpose limitation, access control, encryption in transit and at rest where supported, retention limits, and secure deletion. Review KVKK obligations and any other applicable child-data/privacy requirements before production data collection; document decisions and obtain qualified review where needed.
- Do not claim legal compliance solely because these engineering controls exist.

## Security

- Treat all user input, uploaded files, provider output, and imported source data as untrusted. Validate types, sizes, formats, and content; use safe parsing and output encoding.
- Enforce authorization and answer evaluation on the server. Do not rely on hidden UI controls for access control.
- Protect API routes against abuse with appropriate validation, rate limits, and bounded resource use. Avoid leaking stack traces, secrets, or personal data to clients.
- Review dependency and configuration changes for security impact. Do not add unnecessary tracking, permissions, or third-party data transfer.

## Gamification, XP, avatars, and UI

- XP and rewards should reflect meaningful learning activity. Prevent farming through repeated trivial actions, replayed submissions, duplicate events, client-side score edits, or unbounded retries. Award authoritative XP server-side or through a trusted, idempotent event path.
- Make XP/reward rules understandable. Avoid punitive streak mechanics, manipulative pressure, pay-to-win dynamics, or public comparisons that expose student performance.
- Keep avatar selection inclusive and non-stereotyping. Store only the minimum preference needed; do not infer sensitive traits from avatar choice.
- Preserve the current visual language and responsive behavior. UI changes should support comprehension, accessibility, and low-friction learning. Ensure loading, empty, success, and error states are handled and that privacy messaging matches actual behavior.

## Git and change management

- Inspect `git status`, the current branch, and the relevant diff before editing. Preserve unrelated user changes; never reset, clean, or overwrite them.
- Use a focused branch and descriptive commits when a branch/commit is requested or established by the task. Do not push, merge, publish, or rewrite shared history unless explicitly authorized.
- Make small, reviewable, reversible changes. Before risky edits, create an appropriate backup or use Git to preserve the current state; do not use backups as a substitute for understanding the change.
- Never blindly replace whole files. Read the existing file, make the smallest coherent edit, and inspect the resulting diff.
- Keep generated build output, local databases, secrets, and personal/student data out of commits.
- Document durable architecture, source-policy, data-model, privacy, and product decisions in the appropriate project documentation, including rationale and consequences.

## Required workflow

1. Restate the requested outcome and scope; identify constraints and relevant project instructions.
2. Inspect repository status, branch, relevant files, existing architecture, and available commands before changing anything.
3. For non-trivial work, write a short implementation plan and identify data, privacy, UI, migration, and security impacts.
4. Implement the smallest coherent change. Preserve existing UI/architecture unless an explicit plan requires a change. Keep source material immutable and secrets private.
5. Review the full diff for scope, correctness, regressions, provenance, and accidental sensitive data.
6. Run applicable checks after code changes: at minimum `npm run build` and relevant tests. The current project defines `npm run test:ai`; it does not currently define a general `npm test` script. If a required check cannot run, report why and what remains unverified. Do not claim a check passed unless it actually did.
7. Report changed files, behavior, checks and outcomes, remaining risks, and `git status`/diff summary. Ask the Product Owner about unresolved product decisions; do not silently invent policy.

For a documentation-only change, run relevant format/lint checks if available; do not run unrelated build steps unless the change affects code or build behavior.

## Definition of Done

A task is complete only when all applicable items are true:

- The requested outcome and acceptance criteria are met, with scope limited to the authorized files and behavior.
- Existing UI, architecture, and unrelated work are preserved unless the approved plan says otherwise.
- LGS date limits, curriculum layer, source provenance, verification state, answer-key privacy, H1–H7 consistency, and privacy rules are respected where applicable.
- Secrets and student personal data are absent from changed files, logs, and Git changes.
- The final diff is focused, understandable, and reviewed; risky edits have a recoverable backup/state.
- Required applicable build/tests have run successfully, or limitations are clearly reported without claiming completion of verification.
- Durable decisions and data/source changes are documented with provenance where appropriate.
- The final report names files changed, summarizes implementation and verification, and includes Git status/diff information.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
