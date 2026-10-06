#!/usr/bin/env python3
"""TASK-QBANK-005: canonical görsel temsil + 2022 yapısal kapı onarımı.

Kapsam:
  R9  — görsel-dominant bir MEB sorusunun canonical şemada ve yayın satırında
        doğrulanabilir bir karşılığı var mı? (eski hâli: yoktu)
  R10 — gerçek 2022 staging artefaktı kendi yapısal kapısından geçiyor mu?
        `FEN:Q15` boş option value, `FEN:Q18` eksik option kümesi.

Bu testler **gerçek** artefaktları okur: resmî 2022 staging dosyası ve resmî
PDF'ten üretilmiş kırpma. Sentetik kayıt yalnız kapının reddedici davranışını
(path traversal, eksik görsel kanıt) sınamak için kullanılır.
"""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/source-ingestion"))

from publish_verified import api_row, publish  # noqa: E402
from repair_structural_gate import needs_visual_representation  # noqa: E402
from validate_canonical import (  # noqa: E402
    REQUIRED_CHECKS,
    canonical_fingerprint,
    representation_of,
    validate_record,
    validate_structure,
    validate_visual,
)

STAGING = ROOT / "scripts/source-ingestion/data/questions/staging/MEB-LGS-2022__SAYISAL.json"
REPAIRED = ROOT / "scripts/source-ingestion/data/questions/staging/MEB-LGS-2022__SAYISAL.visual.json"
PDF = ROOT / "scripts/source-ingestion/data/questions/archive/MEB-LGS-2022/01-2022_sayisal_bolum_a_kitapcigi_ve_cevap_anahtari.pdf"
REAL_SHA = "8a1c6526b50b4b695dd6f48bfce42c7fbed53d26f0057e554f666cb4682c4142"
R10_IDS = {"MEB-LGS-2022:SAYISAL:FEN:Q15", "MEB-LGS-2022:SAYISAL:FEN:Q18"}
Q15, Q18 = "MEB-LGS-2022:SAYISAL:FEN:Q15", "MEB-LGS-2022:SAYISAL:FEN:Q18"
STRUCTURED_ID = "MEB-LGS-2022:SAYISAL:MATEMATİK:Q01"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def records_of(doc: dict) -> dict:
    return {record["id"]: record for record in doc["records"]}


class R10StructuralGateTest(unittest.TestCase):
    """Gerçek 2022 artefaktı üzerinde R10'un her iki yarısı."""

    @classmethod
    def setUpClass(cls):
        cls.original = load(STAGING)
        cls.repaired = load(REPAIRED)
        cls.original_records = records_of(cls.original)
        cls.repaired_records = records_of(cls.repaired)

    def test_original_artifact_really_fails_the_gate(self):
        """R10'un birinci yarısı: ham pypdf artefaktı boş/eksik option taşıyor."""
        errors = {rid: validate_record(r) for rid, r in self.original_records.items()}
        failing = {rid for rid, errs in errors.items() if errs}
        self.assertEqual(failing, R10_IDS, "R10 tam olarak bu iki kayıtla sınırlı olmalı")

        q15 = self.original_records[Q15]["question"]
        self.assertIn("D", q15["options"])
        self.assertEqual(q15["options"]["D"].strip(), "", "Q15 D seçeneği boş olmalı")
        self.assertTrue(any("options present but empty: D" in e for e in errors[Q15]))

        q18 = self.original_records[Q18]["question"]
        self.assertEqual(q18["options"], {}, "Q18 seçenek kümesi boş olmalı")
        self.assertTrue(any("missing A-D keys" in e for e in errors[Q18]))

    def test_empty_option_value_and_missing_keys_are_distinct_failures(self):
        """İki bozukluk tipi birbirine karışmamalı, ikisi de ayrı hata üretmeli."""
        empty_value = validate_structure({"grade": 8, "stem": "k", "options": {"A": "1", "B": "2", "C": "3", "D": " "}})
        self.assertTrue(any("present but empty: D" in e for e in empty_value))
        self.assertFalse(any("missing A-D keys" in e for e in empty_value))

        missing_keys = validate_structure({"grade": 8, "stem": "k", "options": {"A": "1", "B": "2"}})
        self.assertTrue(any("missing A-D keys: C, D" in e for e in missing_keys))
        self.assertFalse(any("present but empty" in e for e in missing_keys))

    def test_repaired_artifact_passes_the_real_gate(self):
        """R10'un ikinci yarısı: onarılmış gerçek artefaktın tamamı geçer."""
        failing = {rid for rid, r in self.repaired_records.items() if validate_record(r)}
        self.assertEqual(failing, set())
        self.assertEqual(len(self.repaired_records), self.original["candidate_count"])

    def test_repair_changes_only_the_broken_records(self):
        # TASK-QBANK-011: `extraction.retrieved_at` is a volatile run
        # timestamp, not structural content. The repaired artifact was built
        # from the contaminated 2026-10-04 worktree while the restored
        # original carries the pristine 2026-10-01 stamp, so raw equality
        # flags all 34 records. Compare with that field normalized; the
        # integrity contract is that only R10 records change structurally.
        def _normalized(record: dict) -> dict:
            clone = copy.deepcopy(record)
            clone.get("extraction", {}).pop("retrieved_at", None)
            return clone
        changed = {
            rid for rid in self.original_records
            if _normalized(self.original_records[rid]) != _normalized(self.repaired_records[rid])
        }
        self.assertEqual(changed, R10_IDS, "temsil edilebilen kayıtlar değişmemeli")

    def test_structurally_complete_records_are_left_untouched(self):
        # TASK-QBANK-011: same volatile-timestamp normalization as above.
        # Structural equality (visual absent, STRUCTURED_TEXT, full record
        # match) is preserved; only `extraction.retrieved_at` is ignored.
        for rid, record in self.repaired_records.items():
            if rid in R10_IDS:
                continue
            self.assertIsNone(record["question"].get("visual"), rid)
            self.assertEqual(representation_of(record), "STRUCTURED_TEXT", rid)
            expected = copy.deepcopy(self.original_records[rid])
            actual = copy.deepcopy(record)
            expected.get("extraction", {}).pop("retrieved_at", None)
            actual.get("extraction", {}).pop("retrieved_at", None)
            self.assertEqual(expected, actual, rid)

    def test_repair_invents_no_option_or_answer(self):
        for rid in R10_IDS:
            record = self.repaired_records[rid]
            self.assertIsNone(record["question"]["stem"])
            self.assertIsNone(record["question"]["options"])
            self.assertIsNone(record["answer_key"]["answer"], "cevap asla üretilmemeli")
            self.assertIsNone(record["solution"])
            self.assertIn(record["answer_key"]["candidate"], {"A", "B", "C", "D"},
                          "yalnız resmî aday anahtar korunur")

    def test_repair_never_verifies_or_publishes(self):
        self.assertEqual(self.repaired["status"], "NEEDS_REVIEW")
        self.assertFalse(self.repaired["published"])
        for rid, record in self.repaired_records.items():
            self.assertEqual(record["status"], "NEEDS_REVIEW", rid)
            self.assertFalse(any(record["checks"].values()), rid)

    def test_needs_visual_representation_selects_only_broken_records(self):
        selected = {rid for rid, r in self.original_records.items() if needs_visual_representation(r)}
        self.assertEqual(selected, R10_IDS)


class R9CanonicalVisualTest(unittest.TestCase):
    """Görsel-dominant temsilin canonical karşılığı (R9)."""

    def setUp(self):
        self.records = records_of(load(REPAIRED))
        self.visual = {rid: r for rid, r in self.records.items() if r["question"].get("visual")}

    def test_image_backed_records_exist_and_validate(self):
        self.assertEqual(set(self.visual), R10_IDS)
        for rid, record in self.visual.items():
            with self.subTest(record=rid):
                self.assertEqual(representation_of(record), "IMAGE_BACKED")
                self.assertEqual(validate_record(record), [])

    def test_visual_is_bound_to_the_official_pdf_and_real_crop(self):
        for rid, record in self.visual.items():
            with self.subTest(record=rid):
                visual = record["question"]["visual"]
                self.assertEqual(record["source"]["source_sha256"], REAL_SHA)
                self.assertEqual(visual["authority"], "ORIGINAL_MEB_PDF")
                self.assertFalse(visual["reconstructed_from_ocr"])
                self.assertGreaterEqual(visual["render_dpi"], 150)
                asset = ROOT / visual["asset_path"]
                self.assertTrue(asset.is_file(), f"kırpma eksik: {asset}")
                self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(), visual["asset_sha256"])
                self.assertGreater(asset.stat().st_size, 5000)
                self.assertEqual(visual["page"], record["question"]["page_start"])

    def test_missing_structured_text_is_not_a_valid_question_by_itself(self):
        """`stem/options` eksikliği tek başına geçerli soru anlamına gelmez."""
        stripped = copy.deepcopy(self.visual[Q15])
        stripped["question"]["visual"] = None
        errors = validate_record(stripped)
        self.assertTrue(any("requires a visual block" in e for e in errors), errors)

    def test_missing_or_forged_visual_evidence_fails(self):
        record = copy.deepcopy(self.visual[Q18])
        record["question"]["visual"]["asset_sha256"] = "not-a-hash"
        self.assertTrue(validate_visual(record))

        record = copy.deepcopy(self.visual[Q18])
        record["question"]["visual"]["reconstructed_from_ocr"] = True
        self.assertTrue(validate_visual(record))

        record = copy.deepcopy(self.visual[Q18])
        del record["question"]["visual"]["clip_rect_pt"]
        self.assertTrue(validate_visual(record))

    def test_asset_paths_cannot_escape_the_repository(self):
        """Path traversal / arbitrary file serving yüzeyi kapalı olmalı."""
        for hostile in (
            "../../etc/passwd.png",
            "/etc/passwd.png",
            "public/../../secrets.png",
            "https://evil.example.com/x.png",
            "data/questions/archive/MEB-LGS-2022/x.pdf",
        ):
            record = copy.deepcopy(self.visual[Q15])
            record["question"]["visual"]["asset_path"] = hostile
            with self.subTest(path=hostile):
                self.assertTrue(validate_visual(record), f"reddedilmeliydi: {hostile}")
                self.assertTrue(validate_record(record))

    def test_unsupported_representation_is_rejected(self):
        record = copy.deepcopy(self.records[Q15])
        record["question"]["representation"] = "AUDIO"
        self.assertTrue(any("unsupported question representation" in e for e in validate_record(record)))

    def test_image_backed_record_cannot_carry_partial_options(self):
        record = copy.deepcopy(self.visual[Q15])
        record["question"]["options"] = {"A": "1", "B": "2"}
        self.assertTrue(any("partial A-D" in e for e in validate_record(record)))

    def test_stemless_records_get_distinct_fingerprints(self):
        """R11: iki boş gövdeli görsel soru birbirinin kopyası sayılmamalı."""
        self.assertNotEqual(canonical_fingerprint(self.records[Q15]),
                            canonical_fingerprint(self.records[Q18]))

    def _verified_record(self, rid: str) -> dict:
        """Görsel satırın yayın kapısından geçebilmesi için gereken insan girdisi."""
        record = copy.deepcopy(self.records[rid])
        record["status"] = "VERIFIED"
        record["solution"] = "İncelenmiş çözüm."
        record["answer_key"]["answer"] = "A"
        record["answer_key"]["source_verified"] = True
        record["answer_key"]["answer_key_verified"] = True
        record["curriculum"]["LGS_REFERENCE_2018_PLUS"] = {
            "status": "VERIFIED", "version": "2018+", "subject": "Fen Bilimleri", "unit": "Elektrik",
            "topic": "Yüklenme", "learning_outcome": "Kanıtlı kazanım", "skill": "Çıkarım",
            "evidence_url": "https://meb.gov.tr/cur.pdf",
        }
        record["checks"] = {key: True for key in REQUIRED_CHECKS}
        return record

    def test_api_row_carries_visual_without_leaking_internal_paths(self):
        record = self._verified_record(Q15)
        self.assertEqual(validate_record(record, require_verified=True), [])
        row = api_row(record)
        self.assertEqual(row["representation"], "IMAGE_BACKED")
        self.assertTrue(row["visual"]["publicPath"].startswith("/pilot-2022-visual/"))
        self.assertNotIn("asset_path", row["visual"])
        self.assertNotIn("asset_sha256", row["visual"])
        # Yayın satırı resmî cevabı sunucuda tutmaya devam eder.
        self.assertEqual(row["answer"], "A")

    def test_structured_record_is_unaffected_by_the_visual_model(self):
        """Karşılaştırmalı kontrol: normal metin sorusu değişmeden geçer."""
        record = copy.deepcopy(self.records[STRUCTURED_ID])
        self.assertEqual(representation_of(record), "STRUCTURED_TEXT")
        self.assertEqual(validate_record(record), [])
        self.assertIsNone(record["question"].get("visual"))
        verified = self._verified_record(STRUCTURED_ID)
        row = api_row(verified)
        self.assertEqual(row["representation"], "STRUCTURED_TEXT")
        self.assertIsNone(row["visual"])


class UnpublishedDataCannotReachProductionTest(unittest.TestCase):
    """NEEDS_REVIEW / yayınlanmamış veri üretim akışına sızmaz."""

    def test_publish_ignores_every_staging_record(self):
        self.assertEqual(publish(load(STAGING)), [])
        self.assertEqual(publish(load(REPAIRED)), [])

    def test_api_bank_is_still_empty(self):
        rows = load(ROOT / "data/questions/questions.json")
        self.assertEqual(rows, [], "hiçbir MEB kaydı yayın satırına taşınmamalı")

    def test_visual_records_do_not_leak_into_the_calis_demo_bank(self):
        """`/calis` demo bankasına görsel staging verisi sızmamalı."""
        content = (ROOT / "data/content.ts").read_text(encoding="utf-8")
        for rid in R10_IDS:
            self.assertNotIn(rid, content)
        self.assertNotIn("pilot-2022-visual", content)
        self.assertNotIn("MEB-LGS-2022", content)

    def test_api_route_strips_the_answer_for_visual_rows(self):
        """Görsel temsil eklenmesi cevap anahtarı sızıntısı yaratmamalı."""
        route = (ROOT / "app/api/questions/route.ts").read_text(encoding="utf-8")
        self.assertIn("answer: _answer, verification: _verification, sourceHash: _hash", route)
        self.assertIn("timingSafeEqual(submitted, expected)", route)
        self.assertNotIn("asset_path", route.split("function toPublicQuestion")[1].split("export")[0])


if __name__ == "__main__":
    unittest.main()
