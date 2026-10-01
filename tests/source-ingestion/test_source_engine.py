import json
import sys
import unittest
import hashlib
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/source-ingestion"))
from validate_source_registry import validate
from build_review_queue import build
from create_ingestion_manifest import create_manifest


class SourceRegistryTests(unittest.TestCase):
    def test_final_registry_uses_supported_official_sources(self):
        registry = json.loads((ROOT / "data/source-engine/config/source-registry.json").read_text(encoding="utf-8"))
        self.assertEqual(validate(registry), [])

    def test_rejects_old_lgs_and_non_meb_urls(self):
        source = {"id": "old", "type": "REAL_LGS", "year": 2017, "official_index_url": "https://odsgm.meb.gov.tr/x"}
        self.assertTrue(any("pre-2018" in issue for issue in validate({"sources": [source]})))
        source["year"] = 2018
        source["official_index_url"] = "https://meb.gov.tr.attacker.example/x"
        self.assertTrue(any("official MEB" in issue for issue in validate({"sources": [source]})))

    def test_pdf_manifest_hash_and_review_status(self):
        registry = json.loads((ROOT / "data/source-engine/config/source-registry.json").read_text(encoding="utf-8"))
        source = next(item for item in registry["sources"] if item["id"] == "MEB-LGS-2025")
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / "sample.pdf"
            content = b"%PDF-1.4\nsynthetic test bytes"
            pdf.write_bytes(content)
            manifest = create_manifest(pdf, source, source["official_index_url"])
        self.assertEqual(manifest["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(manifest["status"], "NEEDS_REVIEW")
        self.assertFalse(manifest["published"])
        self.assertEqual(manifest["resulting_record_count"], 0)

    def test_manifest_rejects_non_meb_and_unregistered_urls(self):
        registry = json.loads((ROOT / "data/source-engine/config/source-registry.json").read_text(encoding="utf-8"))
        source = next(item for item in registry["sources"] if item["id"] == "MEB-LGS-2025")
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / "sample.pdf"
            pdf.write_bytes(b"synthetic")
            with self.assertRaises(ValueError):
                create_manifest(pdf, source, "https://meb.gov.tr.attacker.example/file.pdf")
            with self.assertRaises(ValueError):
                create_manifest(pdf, source, "https://odsgm.meb.gov.tr/unregistered")

    def test_review_items_are_never_auto_verified(self):
        queue = build({"blocks": [{"question_number": 1, "answer_match_status": "MATCHED"}]})
        self.assertEqual(queue["items"][0]["status"], "NEEDS_REVIEW")
        self.assertFalse(any(queue["items"][0]["checks"].values()))

    def test_duplicate_candidates_are_flagged_for_human_review(self):
        block = {"question_number": 1, "stem": "  Soru  metni ", "options": {"A": "1"}}
        queue = build({"blocks": [block, {**block, "question_number": 2, "stem": "soru metni"}]})
        self.assertEqual(queue["items"][0]["status"], "NEEDS_REVIEW")
        self.assertEqual(queue["items"][0]["possible_duplicate_indices"], [1])
        self.assertFalse(queue["items"][0]["checks"]["duplicate_checked"])


if __name__ == "__main__":
    unittest.main()
