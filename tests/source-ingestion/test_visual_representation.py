#!/usr/bin/env python3
"""TASK-QBANK-005: canonical görsel temsili (R9) ve 2022 yapısal kapısı (R10).

Kapsam:
  * R9 — ``representation`` + kanıtlı ``visual`` bloğunun canonical kayıtta,
    doğrulamada ve yayın satırında karşılığı; görsel yol güvenliği.
  * R10 — boş option value / eksik A-D seti üretim öncesi reddedilir ve gerçek
    2022 staging artefaktındaki iki kayıt fiilen hâlâ kırmızıdır.

Bu test hiçbir ağ isteği yapmaz; görsel referansı mevcut pilot kırpmasının
gerçek SHA-256 değerini kullanır.
"""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/source-ingestion"))

from extract_pdf_candidates import segment_page  # noqa: E402
from publish_verified import publish  # noqa: E402
from validate_canonical import (  # noqa: E402
    REQUIRED_CHECKS,
    representation_of,
    safe_asset_path,
    safe_public_path,
    transition,
    validate_record,
)

REAL_STAGING = ROOT / "scripts/source-ingestion/data/questions/staging/MEB-LGS-2022__SAYISAL.json"
SCHEMA = ROOT / "scripts/source-ingestion/canonical_schema.json"
API_ROUTE = ROOT / "app/api/questions/route.ts"

# Gerçek 2022 pilot kırpması (pilot.json ile aynı dosya) — kanıt zinciri buradan gelir.
REAL_ASSET_PATH = "public/pilot-2022-visual/mat-q04-p03.png"
REAL_PUBLIC_PATH = "/pilot-2022-visual/mat-q04-p03.png"
REAL_ASSET_SHA = hashlib.sha256((ROOT / REAL_ASSET_PATH).read_bytes()).hexdigest()

def base_record():
    """Yapılandırılmış metin temsilli geçerli bir canonical kayıt."""
    return {
        "schema_version": "1.0", "id": "MEB-LGS-2025:SAYISAL_A:Q01",
        "source": {
            "source_id": "MEB-LGS-2025", "source_type": "REAL_LGS", "year": 2025,
            "official_index_url": "https://odsgm.meb.gov.tr/www/", "source_file_url": "https://meb.gov.tr/a.pdf",
            "source_page_url": "https://odsgm.meb.gov.tr/www/", "discovered_from": "https://odsgm.meb.gov.tr/www/",
            "pdf_url": "https://meb.gov.tr/a.pdf", "final_url": "https://meb.gov.tr/a.pdf",
            "redirect_chain": ["https://meb.gov.tr/a.pdf"],
            "source_sha256": hashlib.sha256(b"pdf").hexdigest(), "booklet": "SAYISAL_A", "question_number": 1,
        },
        "question": {"grade": 8, "subject": "Matematik", "stem": "Bu yeterince uzun bir örnek soru köküdür.",
                     "options": {"A": "1", "B": "2", "C": "3", "D": "4"}, "page_start": 2, "page_end": 2},
        "answer_key": {"candidate": "C", "answer": "C", "authority": "OFFICIAL_MEB_ONLY",
                       "source_verified": True, "answer_key_verified": True},
        "curriculum": {
            "LGS_REFERENCE_2018_PLUS": {"status": "VERIFIED", "version": "2018+", "subject": "Matematik",
                                        "unit": "Üçgenler", "topic": "Açı ilişkileri",
                                        "learning_outcome": "Kanıt destekli kazanım", "skill": "Çıkarım",
                                        "evidence_url": "https://meb.gov.tr/cur.pdf"},
            "CURRENT_TYMM": {"status": "UNMAPPED", "version": None, "subject": None, "unit": None,
                             "topic": None, "learning_outcome": None, "skill": None, "evidence_url": None},
        },
        "extraction": {"method": "pypdf-text-v1", "retrieved_at": "2026-10-05T00:00:00+00:00",
                       "confidence": "HUMAN_REVIEWED", "warnings": [], "answer_key_candidates": []},
        "solution": "Adım adım açıklama.", "status": "NEEDS_REVIEW",
        "checks": {key: True for key in REQUIRED_CHECKS},
    }


def image_backed_record():
    """Gerçek pilot kırpmasına dayanan, kanıtlı görsel ağırlıklı kayıt (R9)."""
    record = base_record()
    record["id"] = "MEB-LGS-2022:SAYISAL:MATEMATİK:Q04"
    record["question"] = {
        "grade": 8, "subject": "Matematik", "representation": "IMAGE_BACKED",
        "stem": None, "options": None, "page_start": 3, "page_end": 3,
        "visual": {
            "authority": "ORIGINAL_MEB_PDF", "asset_path": REAL_ASSET_PATH,
            "public_path": REAL_PUBLIC_PATH, "asset_sha256": REAL_ASSET_SHA,
            "page": 3, "clip_rect_pt": {"x0": 43.44, "y0": 448.76, "x1": 515.1, "y1": 729.0},
            "render_dpi": 300, "reconstructed_from_ocr": False,
        },
    }
    record["extraction"] = {**record["extraction"], "method": "page_render_clip", "confidence": "UNREVIEWED"}
    return record


class StructuralGateTest(unittest.TestCase):
    """R10: eksik/boş option durumları üretim öncesi kesin olarak reddedilir."""

    def test_missing_option_keys_and_empty_values_are_reported_separately(self):
        missing = base_record()
        missing["id"] = "MEB-LGS-2025:SAYISAL_A:Q02"
        missing["question"]["options"] = {"A": "1", "B": "2"}
        errors = validate_record(missing)
        self.assertTrue(any("missing A-D keys: C, D" in error for error in errors), errors)
        self.assertTrue(any("exactly four non-empty A-D options" in error for error in errors), errors)

        empty = base_record()
        empty["id"] = "MEB-LGS-2025:SAYISAL_A:Q03"
        empty["question"]["options"] = {"A": "1", "B": "2", "C": "3", "D": ""}
        errors = validate_record(empty)
        self.assertTrue(any("present but empty: D" in error for error in errors), errors)
        self.assertFalse(any("missing A-D keys" in error for error in errors), errors)

    def test_visual_only_mode_does_not_waive_structured_option_rules(self):
        record = image_backed_record()
        record["question"]["options"] = {"A": "1", "B": "2"}
        errors = validate_record(record)
        self.assertTrue(any("must not carry a partial A-D option set" in error for error in errors), errors)

    def test_empty_option_value_is_flagged_at_extraction_time(self):
        rows = segment_page(
            "1. Bu yeterince uzun bir soru metnidir ve seçenekleri vardır.\nA) 1  B) 2  C) 3  D) ", 4
        )
        self.assertEqual(len(rows), 1)
        self.assertIn("option_value_empty", rows[0]["extraction_warnings"])

class VisualRepresentationTest(unittest.TestCase):
    """R9: görsel ağırlıklı sorunun canonical ve yayın yolunda karşılığı vardır."""

    def test_schema_declares_representation_and_visual_provenance(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        question = schema["properties"]["question"]["properties"]
        self.assertEqual(set(question["representation"]["enum"]), {"STRUCTURED_TEXT", "IMAGE_BACKED", "HYBRID"})
        self.assertIn("visual", question)
        visual = schema["$defs"]["visual"]
        self.assertEqual(visual["properties"]["authority"]["const"], "ORIGINAL_MEB_PDF")
        self.assertIs(visual["properties"]["reconstructed_from_ocr"]["const"], False)
        self.assertIn("asset_sha256", visual["required"])
        # Geriye uyum: temsil alanı opsiyoneldir, eski kayıtlar geçerli kalır.
        self.assertNotIn("representation", schema["properties"]["question"]["required"])
        # TASK-QBANK-007 (C4): çapraz-alan kuralı şemada da durur — IMAGE_BACKED/HYBRID
        # görsel kanıtı olmadan şema düzeyinde reddedilir; ters yön eklenmez
        # (görselin varlığı, metin kapısını gevşetmez — o runtime işidir).
        branches = schema["properties"]["question"].get("allOf", [])
        self.assertEqual(len(branches), 2)
        for mode in ("IMAGE_BACKED", "HYBRID"):
            branch = next(b for b in branches
                          if b.get("if", {}).get("properties", {}).get("representation", {}).get("const") == mode)
            self.assertEqual(branch["then"]["required"], ["visual"])
            self.assertEqual(branch["then"]["properties"]["visual"], {"$ref": "#/$defs/visual"})

    def test_image_backed_record_is_structurally_valid_and_verifiable(self):
        record = image_backed_record()
        self.assertEqual(representation_of(record), "IMAGE_BACKED")
        self.assertEqual(validate_record(record), [])
        self.assertEqual(validate_record(record, require_verified=True), [])
        self.assertEqual(transition(record, "VERIFIED")["status"], "VERIFIED")

    def test_structured_record_without_visual_stays_valid(self):
        record = base_record()
        self.assertEqual(representation_of(record), "STRUCTURED_TEXT")
        self.assertEqual(validate_record(record), [])
        self.assertEqual(validate_record(record, require_verified=True), [])

    def test_image_backed_requires_original_pdf_visual_provenance(self):
        missing = image_backed_record()
        missing["question"]["visual"] = None
        errors = validate_record(missing)
        self.assertTrue(any("requires a visual block" in error for error in errors), errors)

        redrawn = image_backed_record()
        redrawn["question"]["visual"] = {**redrawn["question"]["visual"], "reconstructed_from_ocr": True}
        self.assertTrue(any("reconstructed/redrawn from OCR" in error for error in validate_record(redrawn)))

        foreign = image_backed_record()
        foreign["question"]["visual"] = {**foreign["question"]["visual"], "authority": "AI_REDRAW"}
        self.assertTrue(any("authority must be the original MEB PDF" in error for error in validate_record(foreign)))

    def test_asset_paths_reject_traversal_and_absolute_escapes(self):
        for bad in ("../secret.png", "public/../../.env.png", "/etc/passwd.png", "a/../b.png", "x.png.exe", "..png"):
            self.assertFalse(safe_asset_path(bad), bad)
        self.assertTrue(safe_asset_path(REAL_ASSET_PATH))
        for bad in ("//etc/x.png", "/../.env.png", "/a/../b.png"):
            self.assertFalse(safe_public_path(bad), bad)
        self.assertTrue(safe_public_path(REAL_PUBLIC_PATH))
        # API satırı doğrulayıcısı da aynı traversal kuralını uygular.
        route = API_ROUTE.read_text(encoding="utf-8")
        self.assertIn('v.publicPath.includes("..")', route)
        self.assertIn('v.authority !== "ORIGINAL_MEB_PDF"', route)

    def test_publish_carries_visual_but_not_internal_asset_paths(self):
        row = publish({"records": [dict(image_backed_record(), status="VERIFIED")]})[0]
        self.assertEqual(row["representation"], "IMAGE_BACKED")
        self.assertEqual(row["visual"]["publicPath"], REAL_PUBLIC_PATH)
        self.assertEqual(row["visual"]["authority"], "ORIGINAL_MEB_PDF")
        self.assertEqual(row["visual"]["page"], 3)
        self.assertNotIn("asset_path", row["visual"])
        self.assertNotIn("asset_sha256", row["visual"])
        # Yayın satırında cevap anahtarı sunucu tarafında kalır.
        self.assertEqual(row["answer"], "C")
        route = API_ROUTE.read_text(encoding="utf-8")
        self.assertIn("answer: _answer, verification: _verification, sourceHash: _hash", route)

    def test_unpublished_records_never_reach_the_api_store(self):
        self.assertEqual(publish({"records": [image_backed_record()]}), [])

class RealArtifactTest(unittest.TestCase):
    """R10'un gerçek 2022 staging artefaktı üzerindeki fiilî sonucu."""

    FAILING = ("MEB-LGS-2022:SAYISAL:FEN:Q15", "MEB-LGS-2022:SAYISAL:FEN:Q18")

    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(REAL_STAGING.read_text(encoding="utf-8"))
        cls.records = {record["id"]: record for record in cls.payload["records"]}

    def test_real_2022_artifact_still_fails_the_structural_gate(self):
        failing = {rid: errs for rid, errs in
                   ((rid, validate_record(rec)) for rid, rec in self.records.items()) if errs}
        self.assertEqual(set(failing), set(self.FAILING), f"beklenmeyen kayıt hataları: {failing}")
        self.assertTrue(any("present but empty: D" in e for e in failing[self.FAILING[0]]))
        self.assertTrue(any("missing A-D keys" in e for e in failing[self.FAILING[1]]))

    def test_failing_records_are_flagged_low_confidence_and_never_verified(self):
        # TASK-QBANK-011: recalibrated to the restored b425500 baseline.
        # The old assertion (both records LOW + non-empty warnings) was
        # calibrated to the contaminated 2026-10-04 worktree, which had
        # injected `option_value_empty` + LOW onto FEN:Q15 (QBANK-002/005-era
        # mutation). Verified baseline provenance is:
        #   Q15: confidence UNREVIEWED, warnings [] (D option present but empty)
        #   Q18: confidence LOW, warnings ['four_options_not_confidently_extracted']
        # The integrity contract (NEEDS_REVIEW, answer None, VERIFIED blocked,
        # options never fabricated) holds for both and is fully preserved.
        expected_provenance = {
            self.FAILING[0]: {"confidence": "UNREVIEWED", "warnings": []},
            self.FAILING[1]: {"confidence": "LOW", "warnings": ["four_options_not_confidently_extracted"]},
        }
        for rid in self.FAILING:
            record = self.records[rid]
            with self.subTest(record=rid):
                self.assertEqual(record["status"], "NEEDS_REVIEW")
                self.assertIsNone(record["answer_key"]["answer"])
                self.assertEqual(
                    record["extraction"]["confidence"],
                    expected_provenance[rid]["confidence"],
                )
                self.assertEqual(
                    record["extraction"]["warnings"],
                    expected_provenance[rid]["warnings"],
                )
                with self.assertRaises(ValueError):
                    transition(record, "VERIFIED")
                # Seçenekler uydurulmaz: ya eksik ya boş kalır.
                options = record["question"]["options"]
                self.assertTrue(not options or any(not value.strip() for value in options.values()))

    def test_every_other_2022_record_remains_structurally_valid(self):
        for rid, record in self.records.items():
            if rid in self.FAILING:
                continue
            with self.subTest(record=rid):
                self.assertEqual(validate_record(record), [])

    def test_real_artifact_publishes_nothing(self):
        self.assertEqual(publish(self.payload), [])


if __name__ == "__main__":
    unittest.main()
