import json
import hashlib
from datetime import datetime, timezone

OFFICIAL_INDEX_URL = "https://odsgm.meb.gov.tr/www/5-haziran-2022-tarihinde-yapilan-sinavla-ogrenci-alacak-ortaogretim-kurumlarina-iliskin-merkezi-sinav-soru-kitapciklari-ve-cevap-anahtarlari/icerik/822"
PDF_URL = "https://cdn.eba.gov.tr/icerik/lgs/2022_sayisal_bolum_a_kitapcigi_ve_cevap_anahtari.pdf"
SOURCE_SHA256 = "8a1c6526b50b4b695dd6f48bfce42c7fbed53d26f0057e554f666cb4682c4142"

def transform_question(q):
    q_num = q["source"]["question_number"]
    page_num = q["source"]["page_number"]

    return {
        "schema_version": "1.0",
        "id": q["id"],
        "source": {
            "source_id": "MEB-LGS-2022",
            "source_type": "REAL_LGS",
            "year": 2022,
            "official_index_url": OFFICIAL_INDEX_URL,
            "source_page_url": OFFICIAL_INDEX_URL,
            "discovered_from": OFFICIAL_INDEX_URL,
            "pdf_url": PDF_URL,
            "final_url": PDF_URL,
            "source_file_url": PDF_URL,
            "redirect_chain": [PDF_URL],
            "source_sha256": SOURCE_SHA256,
            "booklet": "SAYISAL",
            "question_number": q_num
        },
        "question": {
            "grade": 8,
            "subject": "MATEMATİK",
            "stem": q["question"]["stem"],
            "options": q["question"]["options"],
            "page_start": page_num,
            "page_end": page_num
        },
        "answer_key": {
            "candidate": q["answer_key"]["candidate"],
            "answer": None,
            "authority": "OFFICIAL_MEB_ONLY",
            "source_verified": False,
            "answer_key_verified": False
        },
        "curriculum": {
            "LGS_REFERENCE_2018_PLUS": {
                "status": "MAPPED_NEEDS_REVIEW",
                "version": "LGS_REFERENCE_2018_PLUS",
                "subject": "MATEMATİK",
                "unit": q["curriculum"]["unit"],
                "topic": q["curriculum"]["topic"],
                "learning_outcome": q["curriculum"]["learning_outcome"],
                "skill": None,
                "evidence_url": None
            },
            "CURRENT_TYMM": {
                "status": "UNMAPPED",
                "version": None,
                "subject": None,
                "unit": None,
                "topic": None,
                "learning_outcome": None,
                "skill": None,
                "evidence_url": None
            }
        },
        "extraction": {
            "method": "gemini-fullpage-v3",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "confidence": "UNREVIEWED",
            "warnings": [],
            "answer_key_candidates": [],
            "answer_key_map": None
        },
        "solution": None,
        "status": "NEEDS_REVIEW",
        "checks": {
            "source_verified": False,
            "year_verified": False,
            "booklet_verified": False,
            "question_number_verified": False,
            "text_verified": False,
            "options_verified": False,
            "answer_key_source_verified": False,
            "answer_key_verified": False,
            "curriculum_verified": False,
            "solution_verified": False,
            "duplicate_checked": False
        }
    }

with open("scripts/source-ingestion/data/questions/staging/MEB-LGS-2022__SAYISAL_staging.json", "r", encoding="utf-8") as f:
    new_data = json.load(f)

with open("scripts/source-ingestion/data/questions/staging/MEB-LGS-2022__SAYISAL.json", "r", encoding="utf-8") as f:
    main_data = json.load(f)

main_ids = {q["id"] for q in main_data["records"]}

new_records = []
for q in new_data["questions"]:
    if q["id"] not in main_ids:
        transformed = transform_question(q)
        new_records.append(transformed)
        print(f"Dönüştürüldü: {q['id']}")

if new_records:
    main_data["records"].extend(new_records)
    main_data["records"].sort(key=lambda x: x["source"]["question_number"])

    with open("scripts/source-ingestion/data/questions/staging/MEB-LGS-2022__SAYISAL.json", "w", encoding="utf-8") as f:
        json.dump(main_data, f, ensure_ascii=False, indent=2)

    print(f"\n{len(new_records)} yeni soru eklendi. Toplam: {len(main_data['records'])}")
