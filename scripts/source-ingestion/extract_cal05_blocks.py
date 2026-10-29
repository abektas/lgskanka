#!/usr/bin/env python3
"""cal05 multi-subject extractor — crops İnkılap, Din, İngilizce blocks.

cal05 is a mixed book: 3 subject blocks + 2018-2025 Merkezî Sınav blocks.
The Merkezî Sınav blocks are already extracted separately — skip them.
Each block gets its own subject folder + answer key matching.
"""
import sys
sys.path.insert(0, '/home/selam/roller/web/lgs-ai-coach/scripts/source-ingestion')
from extract_study_workbook import crop_page, parse_exam_key_text, sha256
import pypdfium2 as pdfium
import json
from pathlib import Path

PDF = '/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal05.pdf'
OUT_ROOT = Path('/home/selam/roller/web/lgs-ai-coach/lgs_çalışma_soruları')
SRC = Path(PDF)

blocks = {
    'inkilap':   {'pages': (7, 99),   'key_page': 100, 'subject': 'inkilap-tarihi'},
    'din':       {'pages': (101, 182), 'key_page': 183, 'subject': 'din-kulturu'},
    'ingilizce': {'pages': (185, 342), 'key_page': 343, 'subject': 'ingilizce'},
}

doc = pdfium.PdfDocument(PDF)

for block_name, cfg in blocks.items():
    out_dir = OUT_ROOT / cfg['subject']
    out_dir.mkdir(parents=True, exist_ok=True)
    p_start, p_end = cfg['pages']
    key_page = cfg['key_page']

    print(f"\n=== {block_name.upper()} (P{p_start}-{p_end}) ===", flush=True)

    # 1. Parse answer key
    key_text = doc[key_page - 1].get_textpage().get_text_range()
    answers = parse_exam_key_text(key_text)
    print(f"  Cevap anahtari: {len(answers)} cevap (P{key_page})", flush=True)

    # 2. Crop questions
    records = []
    for pno in range(p_start, p_end + 1):
        page = doc[pno - 1]
        head = page.get_textpage().get_text_range()[:400].upper()
        if "CEVAP ANAHTARI" in head or "İÇİNDEKİLER" in head:
            continue
        recs = crop_page(page, pno, out_dir, "cal05")
        for r in recs:
            r['answer'] = answers.get(r['q'])
            r['answerSource'] = 'EXAM_KEY' if r['answer'] else None
            r['status'] = 'NEEDS_REVIEW'
            records.append(r)
        if pno % 20 == 0:
            print(f"  P{pno}: {len(records)} soru (toplam)", flush=True)

    # 3. Match stats
    matched = sum(1 for r in records if r['answer'])
    unmatched = len(records) - matched
    print(f"  Kirpilan: {len(records)} soru, eslesen: {matched}, eslesmeyen: {unmatched}", flush=True)

    # 4. Write outputs
    answers_json = {f'EXAM:CAL05:{block_name}:q{r["q"]:02d}': r['answer'] for r in records if r['answer']}
    (out_dir / 'answers.json').write_text(json.dumps(answers_json, ensure_ascii=False, indent=2))

    manifest = {
        'manifestVersion': '1.0', 'status': 'NEEDS_REVIEW', 'published': False,
        'method': 'shape-aware-v1',
        'render': {'dpi': 300, 'margin_pt': 14.0, 'bbox': 'text UNION significant shapes'},
        'source': {
            'sourceId': f'STUDY-CAL05-{block_name.upper()}',
            'pdf': 'cal05.pdf', 'sha256': sha256(SRC),
            'subject': block_name, 'grade': 8,
        },
        'block': {'pages': [p_start, p_end], 'keyPage': key_page},
        'summary': {'questions': len(records), 'answersMatched': matched, 'answersUnmatched': unmatched},
        'questions': records,
    }
    (out_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"  Kaydedildi: {out_dir}/", flush=True)

doc.close()
print("\n=== TAMAMLANDI ===", flush=True)
