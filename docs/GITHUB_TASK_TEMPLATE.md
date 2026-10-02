# LGS AI Coach — Cline Task Template

> Use this template for GitHub Issues that ChatGPT creates for Cline.

## TASK

**Task ID:** `TASK-<number>`
**Agent:** `Cline`
**Status:** `READY_FOR_CLINE`
**Phase:** `<master-plan phase>`
**Priority:** `<P0/P1/P2>`

## Objective

<One precise statement of the outcome.>

## Why this task exists

<Reference to the approved master-plan step or durable project decision.>

## Scope

### In scope

- ...

### Out of scope

- ...

## Acceptance criteria

- [ ] ...
- [ ] ...
- [ ] ...

## Relevant project sources

- `AGENTS.md`
- `CLINE_BRIEFING.md`
- `docs/CHATGPT_CLINE_COLLABORATION_PROTOCOL.md`
- `LGS_AI_COACH_MASTER_PROJE_PLANI_v2.0.md`
- Relevant source files: ...

## Implementation constraints

- Preserve unrelated work.
- Do not silently change architecture or product behavior outside scope.
- Follow source/provenance, privacy/KVKK and security rules in `AGENTS.md`.
- Do not add secrets or student PII.

## Verification required

- `npm run build`
- Relevant tests: ...
- Additional checks: ...

## Handoff requirement

Create:

`docs/handoffs/TASK-<number>-<short-name>.md`

The report must record actual commands/results, changed files, risks, Git status, and whether a material decision was discovered.

## Completion state

Cline must open a focused PR linked to this Issue and request **ChatGPT review**.

Do not invent the next task. If the implementation reveals a material product/architecture decision, stop and document it for ChatGPT/Product Owner review.
