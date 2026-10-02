# LGS AI Coach — ChatGPT ↔ Cline Collaboration Protocol

**Status:** ACTIVE
**Repository:** `abektas/lgs-ai-coach`
**Source of truth:** GitHub
**Product Owner:** User
**Project Coordinator / Architect / Reviewer:** ChatGPT
**Implementer / Tester / Git Operator:** Cline

## 1. Purpose

This document defines the operating protocol between the Product Owner, ChatGPT and Cline. It exists to eliminate routine manual report transfer and to make GitHub the shared technical source of truth.

The project is advanced through small, auditable tasks. ChatGPT coordinates the sequence; Cline implements and verifies; the Product Owner decides only when a product, scope, architectural or other material decision is required.

## 2. Roles

### Product Owner — User

- Owns product goals, priorities and product behavior.
- Approves material architecture, scope, technology or policy changes.
- Is not required to relay routine implementation reports between ChatGPT and Cline.

### ChatGPT — Project Coordinator, Architect, Planner and Reviewer

ChatGPT is responsible for:

1. Reading the current GitHub state before making a coordination decision.
2. Maintaining continuity with the master project plan and durable project decisions.
3. Reviewing every Cline PR before the next implementation step is authorized by the workflow.
4. Determining whether the PR completes the planned task and whether the next step is already covered by an existing approved plan.
5. Creating the next GitHub task when the next step is already decided and does not require Product Owner approval.
6. Stopping and asking the Product Owner when a material new decision is required.
7. Recording durable decisions in GitHub documentation.

ChatGPT must not silently change the product direction, architecture, scope, curriculum policy, privacy policy, source policy or other durable project decisions.

### Cline — Implementer, Tester and Git Operator

Cline is responsible for:

1. Discovering and accepting GitHub tasks assigned to Cline.
2. Inspecting the repository before implementation.
3. Implementing only the authorized task scope.
4. Running relevant tests and build checks.
5. Creating a focused branch and PR according to the task instructions.
6. Writing the required handoff report in GitHub.
7. Leaving enough evidence for ChatGPT to independently review the result.
8. Stopping after the PR is opened; Cline must not invent the next product or architectural step.

## 3. GitHub is the source of truth

The authoritative project state is the combination of:

- `AGENTS.md`
- `LGS_AI_COACH_MASTER_PROJE_PLANI_v2.0.md`
- durable project documents under `docs/`
- GitHub Issues used as implementation tasks
- GitHub Pull Requests and their diffs
- merged code on the default branch
- relevant source/provenance records

Local notes, chat transcripts and temporary reports are not authoritative when they conflict with GitHub.

## 4. Task lifecycle

The canonical lifecycle is:

```text
PLANNED
  ↓
READY_FOR_CLINE
  ↓
IN_PROGRESS
  ↓
PR_OPEN
  ↓
CHATGPT_REVIEW
  ↓
  ├── PLAN_CONTINUES → NEXT_TASK
  │                         ↓
  │                    READY_FOR_CLINE
  │
  └── MATERIAL_DECISION_REQUIRED
                              ↓
                         PRODUCT_OWNER
                              ↓
                       approved / revised
                              ↓
                         NEXT_TASK
                              ↓
                       READY_FOR_CLINE
```

Suggested GitHub labels:

- `agent:cline`
- `status:ready`
- `status:in-progress`
- `status:pr-open`
- `status:chatgpt-review`
- `status:blocked-owner`
- `status:done`
- `type:implementation`
- `type:bug`
- `type:documentation`
- `type:architecture`

Labels are coordination metadata. The issue body and PR are the authoritative task evidence.

## 5. How Cline learns that a new task exists

### Required task discovery rule

When Cline starts a work session for this repository, it must first inspect GitHub for open issues assigned to Cline or carrying the `agent:cline` + `status:ready` combination.

Cline must not select arbitrary issues. If multiple ready tasks exist, prefer the explicitly assigned/highest-priority task and report the selection before implementation.

### Important operational limitation

A GitHub Issue does **not** inherently wake an already-idle Cline process. GitHub is the task source, but an execution trigger is required to make Cline automatically start work.

Therefore the workflow supports two operating modes:

**Mode A — session-start intake (immediately usable):**

- The user starts Cline or gives Cline the repository/workspace.
- Cline runs the GitHub task-intake procedure.
- Cline finds the `status:ready` task and starts it.

**Mode B — automatic execution (future automation):**

- A local/hosted task watcher receives or polls GitHub events.
- It detects a new `agent:cline` + `status:ready` issue.
- It invokes the approved Cline execution mechanism.
- Cline then follows this protocol.

Do not claim that Mode B exists until the watcher/runner is actually installed, tested and documented in this repository.

## 6. Task intake by Cline

For every newly accepted task, Cline must:

1. Read `AGENTS.md`.
2. Read this protocol.
3. Read the task issue completely.
4. Read the relevant section of the master plan.
5. Inspect repository status, current branch and relevant files.
6. Check for conflicting open work/PRs before editing.
7. Restate the acceptance criteria internally and keep implementation within scope.
8. Move/record the task as `status:in-progress` when the workflow mechanism permits it.

Cline must not begin a task merely because a loosely related issue exists.

## 7. Implementation rules

Cline must follow `AGENTS.md` in full. In particular:

- Preserve existing UI, flows and architecture unless the task explicitly authorizes a change.
- Prefer the smallest coherent and reversible change.
- Do not reset, clean, overwrite or discard unrelated work.
- Keep secrets, student PII, raw voice/photos and local environment data out of Git.
- Respect LGS scope (2018+), curriculum-layer separation and source provenance.
- Keep authoritative answer keys server-side.
- Preserve H1–H7 first-error semantics.
- Treat imported data, user input and provider output as untrusted.
- Read the relevant Next.js documentation under `node_modules/next/dist/docs/` before writing code, as required by `AGENTS.md`.

## 8. Completion requirements for Cline

A task is not complete merely because code was written.

Before opening the PR, Cline must:

1. Review the complete diff.
2. Run the applicable tests.
3. Run `npm run build` for code changes unless a documented technical reason prevents it.
4. Run `npm run test:ai` where applicable.
5. Report every check as PASS, FAIL, BLOCKED or NOT RUN with the reason.
6. Check for secrets/PII in changed files and generated output.
7. Confirm that acceptance criteria are met.
8. Create/update the required handoff report.
9. Create a focused PR linked to the GitHub task.
10. Set the PR/task state to indicate that ChatGPT review is required.

Cline must never report a check as passed unless it actually ran successfully.

## 9. Handoff report

Every implementation PR must contain or link to a handoff report under:

`docs/handoffs/`

Recommended filename:

`docs/handoffs/TASK-<number>-<short-name>.md`

The report must contain:

- Task/Issue number and PR number.
- Objective and acceptance criteria.
- Files changed.
- What was implemented.
- What was deliberately not changed.
- Tests/build commands actually executed.
- Exact outcomes.
- Relevant warnings or limitations.
- Security/privacy/provenance considerations.
- Database/migration implications, if any.
- Git branch and commit information.
- Final `git status` summary.
- Remaining risks.
- Whether the next step is already specified by the existing plan.
- Any finding that may require Product Owner or architectural review.

The report is evidence for review, not a substitute for reviewing the actual diff.

## 10. PR requirements

Every Cline PR should include:

```text
Task: #<issue>
Scope: <short description>

Acceptance criteria:
- ...

Implementation summary:
- ...

Verification:
- command: ... → PASS/FAIL/BLOCKED/NOT RUN

Handoff report:
- docs/handoffs/...

Potential architectural/product decision:
- NONE
  OR
- <precise decision needed>
```

The PR should be focused on one coherent task. Do not combine unrelated refactors.

## 11. What ChatGPT does when a PR arrives

When ChatGPT is alerted that a new PR exists, ChatGPT must not immediately create another task without review.

ChatGPT reviews:

1. The linked task/acceptance criteria.
2. The current master plan and relevant durable decisions.
3. The PR metadata and commits.
4. The complete changed-file list and diff.
5. The handoff report.
6. Test/build evidence.
7. Source provenance where applicable.
8. Privacy/KVKK and security implications where applicable.
9. Regression/scope risks.

ChatGPT then determines the workflow category.

### Category A — Planned continuation

Use this when:

- the task is completed;
- the implementation is consistent with the approved architecture and product direction;
- no material new decision is required; and
- the next step is already established by the master plan or an existing durable decision.

ChatGPT then creates the next GitHub task for Cline and records the reason for the transition.

### Category B — Correction required

Use this when the PR does not satisfy the task or contains a correctable implementation problem that does not require changing the approved product/architecture direction.

ChatGPT records the required correction in GitHub and sends the task back to Cline through a focused follow-up task/PR revision path.

### Category C — Product/architecture decision required

Use this when continuing requires a new or changed decision about architecture, scope, technology, data model, privacy, security, curriculum/source policy, product behavior or another material project rule.

ChatGPT stops automatic progression and asks the Product Owner for a decision.

No new implementation task that depends on the unresolved decision is marked `status:ready`.

## 12. Product Owner approval gate

The Product Owner is not asked to approve routine implementation steps that were already covered by the approved plan.

The Product Owner is asked only when the review identifies a material decision.

The approval request must be concise and contain:

- what changed or was discovered;
- why the existing plan is insufficient;
- the available options, when relevant;
- consequences/trade-offs;
- ChatGPT's recommended interpretation only as technical analysis, not as an unauthorized product decision;
- the exact decision required from the Product Owner.

After approval, ChatGPT records the durable decision in GitHub before issuing dependent implementation work.

## 13. No hidden progression

Cline must not:

- invent a new phase;
- change the master plan;
- replace a technology because it seems preferable;
- redesign the product;
- reinterpret curriculum/source policy;
- weaken tests or security controls;
- merge or deploy without authorization;
- silently broaden task scope.

If Cline discovers something that materially changes the plan, it must document the finding and flag it for ChatGPT review.

## 14. ChatGPT must also avoid hidden progression

ChatGPT must not silently convert a Cline discovery into a new architectural/product decision. When the next step is outside previously approved decisions, ChatGPT must stop at the Product Owner approval gate.

## 15. Completion signal

The canonical signal that Cline has finished an implementation cycle is:

```text
focused PR OPEN
+
required handoff report present
+
verification results reported
+
PR linked to the task
+
PR marked/requested for ChatGPT review
```

A chat message from Cline saying "done" is not sufficient evidence.

## 16. Review signal and next-task creation

The canonical signal that ChatGPT has completed its review is a GitHub review/coordination record plus one of:

- `NEXT_TASK_CREATED` — the approved plan continues;
- `OWNER_DECISION_REQUIRED` — Product Owner input is required;
- `CORRECTION_REQUIRED` — the current implementation needs correction before progression.

These terms should be used consistently in handoff/review documents so the state is machine-readable and human-readable.

## 17. Merge authority

This protocol does not grant automatic merge authority. The Product Owner remains the final authority for project-level decisions. Merge behavior must follow the repository's actual GitHub permissions and any explicitly established merge policy.

Do not claim that a PR is merged unless GitHub confirms it.

## 18. Failure and interruption

If Cline cannot complete a task:

- do not fabricate success;
- document what was completed;
- document the exact blocker and evidence;
- leave the working tree/branch in a recoverable state;
- do not create a misleading PR that claims completion.

If ChatGPT cannot verify a claim from GitHub evidence, it must mark the item `NOT VERIFIED` rather than assuming it is true.

## 19. Operating principle

The intended loop is:

```text
Approved plan
    ↓
GitHub task
    ↓
Cline implementation
    ↓
Tests + handoff
    ↓
GitHub PR
    ↓
ChatGPT review
    ↓
    ├── already-planned next step → create next task → Cline
    │
    └── material new decision → Product Owner → decision recorded → task → Cline
```

The goal is autonomous **execution continuity**, not autonomous **product decision-making**.
