# Nüli QBANK PDF Extractor v1

## Purpose

`nuli_qbank_pdf_extractor.py` is the deterministic source/asset extraction layer for the Nüli LGS QBANK.

It converts an authoritative MEB PDF into high-resolution question-region PNG assets plus a machine-readable extraction manifest. It does **not** create canonical answers, curriculum verification, or `VERIFIED` records.

## Why this exists

The previous quadrant-based prototype assumed four equal page regions. That is useful for a quick pilot but unsafe as a canonical extraction mechanism because real LGS layouts are not guaranteed to align to equal quadrants.

V1 therefore uses:

1. the original PDF as authority;
2. 300 DPI page rendering by default;
3. visible question-number anchors from `pdfplumber.extract_words()`;
4. inferred one/two-column page geometry;
5. question-region crops bounded by the next detected question in the same column;
6. PDF-point crop coordinates as provenance;
7. PNG SHA-256 hashes;
8. a manifest containing warnings and detection confidence.

## Data boundary

```text
MEB PDF
  -> page geometry / visible question anchors
  -> derived PNG asset
  -> extraction manifest
  -> later visual/source review
  -> canonical QBANK staging
  -> human verification
  -> VERIFIED
```

The extractor must never:

- write `answer_key.answer`;
- mark a question `VERIFIED`;
- invent or verify curriculum mappings;
- rewrite mathematical content from model guesses;
- reconstruct diagrams from OCR;
- publish to `data/questions/questions.json`;
- modify `/calis`.

## Provenance contract

Each extracted asset records:

- source PDF path;
- source PDF SHA-256;
- PDF page number;
- PDF-point crop rectangle (`x0`, `y0`, `x1`, `y1`);
- render DPI;
- asset path;
- public path candidate;
- asset SHA-256;
- pixel dimensions;
- detection confidence;
- warnings;
- short text preview for review/navigation.

The PDF-point rectangle is authoritative for reproducing the crop. The PNG is a derived artifact.

This is compatible with the existing canonical visual contract, which requires `ORIGINAL_MEB_PDF`, a safe PNG path, SHA-256, page, crop coordinates, render DPI, and `reconstructed_from_ocr=false`.

## Important limitation

Question-number detection is deliberately conservative. A detected anchor is evidence of a likely question start, not proof of a semantically complete question boundary.

Therefore:

- warnings are preserved;
- ambiguous pages are not silently repaired;
- the manifest is an extraction/review input, not a publication artifact;
- visual review remains mandatory before canonical publication.

## Typical use

```bash
python -m pip install -r scripts/source-ingestion/requirements-pdf-extractor.txt

python scripts/source-ingestion/nuli_qbank_pdf_extractor.py \
  scripts/source-ingestion/data/sources/MEB-LGS-2022_SAYISAL.pdf \
  scripts/source-ingestion/data/questions/extracted/2022-sayisal \
  --dpi 300
```

Pilot only:

```bash
python scripts/source-ingestion/nuli_qbank_pdf_extractor.py \
  scripts/source-ingestion/data/sources/MEB-LGS-2022_SAYISAL.pdf \
  /tmp/nuli-2022-sayisal-pilot \
  --page-start 3 \
  --page-end 5 \
  --dpi 300
```

The extractor does not copy the source PDF. Keep large authoritative PDFs in the project's source-corpus storage strategy and record their SHA-256 in manifests/canonical records.

## Output

```text
<output-dir>/
  manifest.json
  page-003_q-04_c-1.png
  page-003_q-05_c-2.png
  ...
```

`manifest.json` is intentionally separate from canonical QBANK JSON. A later ingestion/review step can use it to construct canonical records without mixing extraction evidence with human verification state.

## Future extensions

V1 is intentionally small. The next safe improvements are:

- stronger question-anchor scoring using font/size/position metadata;
- explicit single-column vs two-column validation;
- detection of page-spanning questions;
- optional image/object density flags;
- crop QA against page boundaries;
- deterministic conversion from manifest to `IMAGE_BACKED`/`HYBRID` visual provenance blocks;
- review UI/report for ambiguous pages.

These should not weaken the existing human-answer gate or provenance requirements.
