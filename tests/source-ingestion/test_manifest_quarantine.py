#!/usr/bin/env python3
"""T5.6 karantina regresyon testleri.

Geçersiz artifact (fullmembershipcertificate.pdf) için üretilmiş manifestlerin
karantinada olduğunu, silinmediğini ve hiçbir şekilde incelemeye/publish'a açık
görünmediğini doğrular. Registry resmî kayıtlarına dokunulmadığını da kontrol eder.
"""
import hashlib
import json
from pathlib import Path
import unittest
class ManifestQuarantineTest(unittest.TestCase):
    """T5.6: geçersiz artifact (sertifika PDF) manifestleri karantinada olmalı."""

    MANIFEST_DIR = Path(__file__).resolve().parents[2] / "scripts" / "source-ingestion" / "data" / "questions" / "manifests"
    BAD_SHA = "cf9b2e3069ebde02ff2354a080c8ef9b84ca35d8204ee6eff40d0574bd5e875a"
    BAD_FILENAME = "24220837_alte_fullmembershipcertificate.pdf"
    ALLOWED_STATUSES = {"NEEDS_REVIEW", "VERIFIED", "REJECTED"}

    def manifests(self):
        return sorted(self.MANIFEST_DIR.glob("*.json"))

    def bad_sha_manifests(self):
        rows = []
        for path in self.manifests():
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("sha256") == self.BAD_SHA:
                rows.append((path, data))
        return rows

    def test_certificate_manifests_exist(self):
        # Karantina testinin anlamli olmasi icin etkilenen kayitlarin durdugunu dogrular.
        self.assertEqual(len(self.bad_sha_manifests()), 6)

    def test_certificate_manifests_are_rejected_and_unpublished(self):
        for path, data in self.bad_sha_manifests():
            with self.subTest(manifest=path.name):
                self.assertEqual(data.get("status"), "REJECTED")
                self.assertIs(data.get("published"), False)
                self.assertTrue((data.get("rejection_reason") or "").strip())
                self.assertTrue((data.get("reviewer") or "").strip())
                self.assertTrue((data.get("rejected_at") or "").strip())
                quarantine = data.get("quarantine") or {}
                self.assertTrue(quarantine.get("quarantined"))
                self.assertIs(quarantine.get("usable_for_question_extraction"), False)
                self.assertIs(quarantine.get("must_not_support_source_claims"), True)

    def test_no_manifest_claims_a_rejected_artifact_as_reviewable_or_verified(self):
        for path, data in self.bad_sha_manifests():
            with self.subTest(manifest=path.name):
                self.assertNotEqual(data.get("status"), "NEEDS_REVIEW")
                self.assertNotEqual(data.get("status"), "VERIFIED")
                self.assertEqual(data.get("resulting_record_count"), 0)
                self.assertIs(data.get("published"), False)

    def test_every_manifest_uses_a_canonical_status(self):
        for path in self.manifests():
            with self.subTest(manifest=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn(data.get("status"), self.ALLOWED_STATUSES)

    def test_quarantined_artifacts_are_retained_and_hashed(self):
        # Kaynak dosyalar immutable: karantina silme degil, isaretlemedir.
        for path, data in self.bad_sha_manifests():
            with self.subTest(manifest=path.name):
                archived = Path(__file__).resolve().parents[2] / data["archive_path_resolved"]
                self.assertTrue(archived.is_file(), f"arşiv dosyası eksik: {archived}")
                digest = hashlib.sha256(archived.read_bytes()).hexdigest()
                self.assertEqual(digest, self.BAD_SHA)
                self.assertEqual(archived.name, self.BAD_FILENAME)

    def test_real_lgs_manifest_is_not_quarantined(self):
        # T5.5 pilotunda indirilen gercek 2022 kitapcigi karantinada olmamali.
        real = [d for _, d in self.bad_sha_manifests() if d.get("status") == "REJECTED"]
        self.assertEqual(len(real), 6)
        good = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in self.manifests()
            if path.name == "MEB-LGS-2022__8a1c6526b50b.json"
        ]
        self.assertEqual(len(good), 1)
        self.assertEqual(good[0]["status"], "NEEDS_REVIEW")
        self.assertIs(good[0]["published"], False)
        self.assertIn("2022_sayisal_bolum_a_kitapcigi", good[0]["original_filename"])

    def test_registry_still_lists_official_meb_sources(self):
        registry = Path(__file__).resolve().parents[2] / "data" / "source-engine" / "config" / "source-registry.json"
        data = json.loads(registry.read_text(encoding="utf-8"))
        ids = [row["id"] for row in data["sources"]]
        for expected in ("MEB-LGS-2022", "MEB-LGS-2023", "MEB-LGS-2024", "MEB-LGS-2025", "MEB-LGS-2026", "MEB-SAMPLE-ARCHIVE"):
            self.assertIn(expected, ids)


if __name__ == "__main__":
    unittest.main()