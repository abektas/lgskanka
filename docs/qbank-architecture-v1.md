# Nüli LGS QBANK Architecture v1

## 1. Objective

Build a source-faithful, provenance-first LGS question bank for Nüli that is queryable by year, subject, grade, unit, topic, learning outcome, skill, difficulty, question type, representation, and validation state.

The QBANK is not merely a collection of question text. Each record must retain enough evidence to answer:

- Where did this question come from?
- Which exact MEB PDF/page supports it?
- Was the visual content preserved faithfully?
- Which curriculum outcome does it target?
- How difficult is it and why?
- Has the answer been independently verified by a human?
- Is it safe to deliver to a student?

## 2. System of record by lifecycle

```text
Official MEB PDF / source corpus
        |
        v
Source registry + SHA-256
        |
        v
PDF extraction / visual assets
        |
        v
Canonical staging QBANK
        |
        v
Deterministic validation
        |
        v
NEEDS_REVIEW
        |
        v
Human review / attestation
        |
        v
VERIFIED canonical QBANK
        |
        v
Operational PostgreSQL / Supabase
        |
        v
Nüli student experience
```

GitHub is the engineering/source-of-truth repository during the canonical-content phase. PostgreSQL/Supabase is the later operational database for delivery and student activity. Large PDFs and derived visual assets must be handled with an explicit storage strategy rather than blindly committed into normal Git history.

## 3. Canonical question dimensions

Every question should be queryable across these dimensions:

- `YEAR`
- `SOURCE`
- `BOOKLET`
- `SUBJECT`
- `GRADE`
- `UNIT`
- `TOPIC`
- `LEARNING_OUTCOME`
- `SKILL`
- `DIFFICULTY`
- `QUESTION_TYPE`
- `REPRESENTATION`
- `VALIDATION_STATUS`

This supports queries such as:

- 2022-2025 Mathematics + hard questions
- one learning outcome + all historical LGS questions
- a student's H1-H7 error pattern + matching outcome + difficulty
- image-backed geometry questions only
- questions suitable for a particular level

## 4. Curriculum hierarchy

```text
Ders
  -> Sınıf
    -> Ünite
      -> Konu
        -> Kazanım
          -> Alt beceri
```

A question should not be reduced to a single free-text topic. Curriculum mappings carry an explicit lifecycle (`UNMAPPED`, `MAPPED_NEEDS_REVIEW`, `VERIFIED`) and evidence.

The existing canonical schema remains authoritative for the exact record shape and validation rules.

## 5. Difficulty model

Difficulty has two stages.

### 5.1 Pedagogical difficulty

Initial classification can use:

- operation step count;
- number of concepts;
- distractor strength;
- multi-outcome / multi-skill requirement;
- visual interpretation;
- abstract reasoning;
- new-generation contextual load;
- direct knowledge / one-step operation as reducing factors.

The output is a 1-5 estimate plus confidence and rationale.

### 5.2 Empirical difficulty

After real student interaction becomes available, update difficulty using:

- success rate;
- discrimination;
- attempts;
- time-to-answer;
- error taxonomy distribution.

Do not overwrite the provenance of the original pedagogical estimate. Keep the two evidence types distinct.

## 6. Representation model

### STRUCTURED_TEXT

Use when the question can be represented without loss as text + mathematical notation + A-D options.

### IMAGE_BACKED

Use when a diagram, graph, table, map, geometric figure, or other visual content is essential to meaning and should remain the authoritative representation.

### HYBRID

Use when structured text is useful but a visual component remains semantically necessary.

Visual provenance must remain tied to the original MEB PDF. OCR must not be treated as an authoritative reconstruction of the visual asset.

## 7. Answer authority

AI may produce a `candidate` answer for review.

AI must never populate the canonical answer as if it were verified.

```text
candidate = review hypothesis
answer = null until human verification
```

The only canonical answer authority is the independently verified official MEB answer evidence under the existing ingestion specification.

## 8. Lifecycle

```text
DRAFT
  -> EXTRACTED
  -> AUTO_CHECKED
  -> NEEDS_REVIEW
  -> VERIFIED
```

`REJECTED` is an explicit terminal rejection path.

No student-facing delivery may bypass the `VERIFIED` publication gate.

## 9. Extraction architecture

```text
MEB PDF
  -> nuli_qbank_pdf_extractor.py
  -> PNG + extraction manifest
  -> visual/source-fidelity review
  -> canonical staging record
  -> validate_canonical.py
  -> NEEDS_REVIEW
```

The extractor is deterministic and model-independent. A multimodal model may assist with analysis later, but it is not the source authority and cannot bypass validation or human review.

## 10. Student delivery boundary

The student application must not consume raw staging records directly.

```text
canonical QBANK
      |
      v
verified delivery/read layer
      |
      v
study session
      |
      v
student UI
      |
      v
attempt + H1-H7 error analysis
```

The delivery layer should expose only the fields needed by the student experience and should never leak canonical answer keys to the browser before grading.

## 11. Operational database target

PostgreSQL is the target relational database. Supabase is an appropriate operational provider because it adds authentication, row-level security, storage, APIs, and realtime capabilities.

The conceptual relational model is:

- `questions`
- `sources`
- `curriculum`
- `question_curriculum`
- `question_difficulty`
- `question_types`
- `visual_assets`
- `answers`
- `student_attempts`
- `error_analysis`

Canonical source content and student-performance data remain logically separated.

## 12. 2022 pilot rule

The 2022 Sayısal pilot remains the first controlled corpus. Do not expand to the full 2018-2026 corpus until the pilot passes source-fidelity, provenance, validation, human-review, and local student-flow checks.

Known 2022 blockers from the previous audit include incomplete source fidelity, missing answer verification, and visual/structured representation decisions. The repair/review process must preserve those gates rather than bypass them.

## 13. Non-goals

This architecture does not authorize:

- fabricated answer keys;
- AI-only `VERIFIED` status;
- paraphrasing MEB questions into canonical source records;
- generated questions mixed into the authoritative MEB corpus;
- publication before human review;
- immediate migration to Supabase before canonical QBANK stability;
- `/calis` changes as part of PDF extraction.

## 14. Definition of a trustworthy question

A question is delivery-ready only when its identity, source, text/options or visual representation, answer authority, curriculum mapping, solution, duplicate status, and required checks satisfy the existing canonical validation contract and the human review requirement.
