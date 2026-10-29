#!/usr/bin/env python3
"""Transform pipeline output (staging) into canonical schema and merge into main file."""
import json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/home/selam/roller/web/lgs-ai-coach')
STAGING_FILE = ROOT / 'scripts/source-ingestion/data/questions/staging/MEB-LGS-2022__SAYISAL_staging.json'
MAIN_FILE = ROOT / 'scripts/source-ingestion/data/questions/staging/MEB-LGS-2022__SAYISAL.json'

MEB_LGS_2022_SRC_ID = 'MEB-LGS-2022'
MEB_LGS_2022_SRC_TYPE = 'REAL_LGS'
MEB_LGS_2022_YEAR = 2022
MEB_LGS_2022_SHA256 = '8a1c6526b50b4b695dd6f48bfce42c7fbed53d26f0057e554f666cb4682c4142'
MEB_LGS_2022_PDF_URL = 'https://cdn.eba.gov.tr/icerik/lgs/2022_sayisal_bolum_a_kitapcigi_ve_cevap_anahtari.pdf'
MEB_LGS_2022_DISCOVERY_URL = 'https://odsgm.meb.gov.tr/www/5-haziran-2022-tarihinde-yapilan-sinavla-ogrenci-alacak-ortaogretim-kurumlarina-iliskin-merkezi-sinav-soru-kitapciklari-ve-cevap-anahtarlari/icerik/822'

def transform_question(q):
    page = q['source'].get('page_number', 1)
    warnings = q.get('warnings', [])
    return {
        'schema_version': '1.0',
        'id': q['id'],
        'source': {
            'source_id': MEB_LGS_2022_SRC_ID,
            'source_type': MEB_LGS_2022_SRC_TYPE,
            'year': MEB_LGS_2022_YEAR,
            'official_index_url': MEB_LGS_2022_DISCOVERY_URL,
            'source_page_url': MEB_LGS_2022_DISCOVERY_URL,
            'discovered_from': MEB_LGS_2022_DISCOVERY_URL,
            'pdf_url': MEB_LGS_2022_PDF_URL,
            'final_url': MEB_LGS_2022_PDF_URL,
            'source_file_url': MEB_LGS_2022_PDF_URL,
            'redirect_chain': [MEB_LGS_2022_PDF_URL],
            'source_sha256': MEB_LGS_2022_SHA256,
            'booklet': 'SAYISAL',
            'question_number': q['source']['question_number']
        },
        'question': {
            'grade': 8,
            'subject': 'MATEMATİK',
            'stem': q['question']['stem'],
            'options': q['question']['options'],
            'page_start': page,
            'page_end': page,
            'representation': q['question']['representation'],
            'visual': None
        },
        'answer_key': {
            'candidate': q['answer_key']['candidate'],
            'answer': None,
            'authority': 'OFFICIAL_MEB_ONLY',
            'source_verified': False,
            'answer_key_verified': False
        },
        'curriculum': {
            'LGS_REFERENCE_2018_PLUS': {
                'status': 'MAPPED_NEEDS_REVIEW',
                'version': 'LGS_REFERENCE_2018_PLUS',
                'subject': 'MATEMATİK',
                'unit': q['curriculum']['unit'],
                'topic': q['curriculum']['topic'],
                'learning_outcome': q['curriculum']['learning_outcome'],
                'skill': None,
                'evidence_url': None
            },
            'CURRENT_TYMM': {
                'status': 'UNMAPPED',
                'version': None,
                'subject': None,
                'unit': None,
                'topic': None,
                'learning_outcome': None,
                'skill': None,
                'evidence_url': None
            }
        },
        'extraction': {
            'method': 'gemini-fullpage-v3',
            'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'confidence': 'UNREVIEWED',
            'warnings': warnings,
            'answer_key_candidates': [],
            'answer_key_map': None
        },
        'solution': None,
        'status': 'NEEDS_REVIEW',
        'checks': {
            'source_verified': False,
            'year_verified': False,
            'booklet_verified': False,
            'question_number_verified': False,
            'text_verified': False,
            'options_verified': False,
            'answer_key_source_verified': False,
            'answer_key_verified': False,
            'curriculum_verified': False,
            'solution_verified': False,
            'duplicate_checked': False
        }
    }

def main():
    with open(STAGING_FILE, 'r', encoding='utf-8') as f:
        pipeline_data = json.load(f)

    with open(MAIN_FILE, 'r', encoding='utf-8') as f:
        main_data = json.load(f)

    # Build existing IDs for deduplication
    existing_ids = {q['id'] for q in main_data.get('records', [])}
    new_records = []
    added_count = 0

    for q in pipeline_data.get('questions', []):
        if q['id'] in existing_ids:
            print(f'Skip (exists): {q["id"]}')
            continue
        transformed = transform_question(q)
        new_records.append(transformed)
        added_count += 1
        print(f'Added: {q["id"]}')

    if new_records:
        main_data.setdefault('records', []).extend(new_records)
        # Sort by question number
        main_data['records'].sort(key=lambda x: x['source']['question_number'])
        # Preserve metadata
        main_data['source_id'] = MEB_LGS_2022_SRC_ID
        main_data['source_sha256'] = MEB_LGS_2022_SHA256

        with open(MAIN_FILE, 'w', encoding='utf-8') as f:
            json.dump(main_data, f, ensure_ascii=False, indent=2)

        print(f'\n{added_count} yeni soru eklendi. Toplam: {len(main_data["records"])}')
    else:
        print('\nYeni soru eklenmedi (tüm mevcut olduğuna göre skip).')

if __name__ == '__main__':
    main()
