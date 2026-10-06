#!/usr/bin/env python3
"""TASK-QBANK-003: 2022 görsel soru pilotu çıktısının bütünlük denetimleri.

Bu test pilot artefaktlarının (pilot.json + PNG kırpmaları) üretim
kurallarını doğrular: provenance, `NEEDS_REVIEW`/`published=false` durumu,
altı etkilenen sorunun varlığı, kontrol sorularının metin yolu ve cevap
anahtarının istemciye sızmaması. PDF'i yeniden işlemez; yalnızca kayıtlı
pilot çıktısını denetler.
"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PILOT_DIR = ROOT / "scripts/source-ingestion/data/questions/pilot-2022-visual"
PILOT = PILOT_DIR / "pilot.json"
PUBLIC_DIR = ROOT / "public/pilot-2022-visual"
PAGE_SRC = ROOT / "app/pilot-2022-visual/page.tsx"

AFFECTED = {4, 10, 11, 12, 14, 19}
REAL_SHA = "8a1c6526b50b4b695dd6f48bfce42c7fbed53d26f0057e554f666cb4682c4142"


def load_pilot():
    return json.loads(PILOT.read_text(encoding="utf-8"))


class PilotArtifactTest(unittest.TestCase):
    def setUp(self):
        self.doc = load_pilot()

    def test_six_affected_questions_present_as_image_backed(self):
        image_backed = {
            r["question"]["question_number"]
            for r in self.doc["records"]
            if r["mode"] == "image"
        }
        self.assertEqual(image_backed, AFFECTED)

    def test_control_questions_use_structured_text(self):
        controls = [r for r in self.doc["records"] if r["mode"] == "control"]
        self.assertGreaterEqual(len(controls), 1)
        for r in controls:
            self.assertEqual(r["question"]["representation"], "STRUCTURED_TEXT")
            self.assertIsNotNone(r["structured_text"])
            self.assertTrue(r["structured_text"]["stem"])
            self.assertFalse(r["baseline"]["produced_question_block"] is False)

    def test_every_record_has_provenance_and_is_unpublished(self):
        for r in self.doc["records"]:
            with self.subTest(question=r["question"]["question_number"]):
                self.assertEqual(r["source"]["source_sha256"], REAL_SHA)
                self.assertTrue(
                    r["source"]["pdf_url"].startswith("https://cdn.eba.gov.tr/")
                )
                self.assertIsInstance(r["question"]["page"], int)
                self.assertEqual(r["extraction"]["method"], "page_render_clip")
                self.assertGreater(r["extraction"]["render_dpi"], 150)
                self.assertFalse(r["extraction"]["reconstructed_from_ocr"])
                self.assertEqual(r["status"], "NEEDS_REVIEW")
                self.assertFalse(r["published"])
                self.assertFalse(r["baseline"]["authoritative"])
        self.assertEqual(self.doc["status"], "NEEDS_REVIEW")
        self.assertFalse(self.doc["published"])
        self.assertEqual(self.doc["source"]["sha256"], REAL_SHA)

    def test_crops_exist_and_are_not_placeholder(self):
        for r in self.doc["records"]:
            with self.subTest(question=r["question"]["question_number"]):
                path = ROOT / r["image"]["path"]
                self.assertTrue(path.exists(), f"eksik kırpma: {path}")
                self.assertGreater(path.stat().st_size, 5000)
                self.assertGreaterEqual(r["image"]["pixel_width"], 800)
                self.assertTrue(r["image"]["public_path"].startswith("/pilot-2022-visual/"))

    def test_image_records_have_no_structured_text(self):
        for r in self.doc["records"]:
            if r["mode"] == "image":
                self.assertIsNone(r["structured_text"])

    def test_pilot_never_carries_official_answer_key(self):
        """Cevap anahtarı alanı pilot çıktısında yer almamalı."""
        blob = PILOT.read_text(encoding="utf-8")
        for banned in ("answer_key", "correct_option", "correct_answer", "Cevap Anahtarı"):
            self.assertNotIn(banned, blob)

        page = PAGE_SRC.read_text(encoding="utf-8")
        for banned in ("answer_key", "correctOption", "dogru_cevap"):
            self.assertNotIn(banned, page)

    def test_unpublished_state_is_rendered_per_record(self):
        """Her kayıt kendi yayın durumunu göstermeli; yalnızca sayfa başlığı yetmez.

        Kaynak kodda tek geçiş, her iki bölüm (görsel + kontrol) tarafından
        paylaşılan bir bileşende olmalıdır. Kontrol bölümü bu bileşeni atlarsa
        denetim sessizce geçer; bu yüzden iki bölümün de durum etiketini
        taşıdığı ayrıca doğrulanır.
        """
        page = PAGE_SRC.read_text(encoding="utf-8")
        self.assertIn("published={String(r.published)}", page)
        self.assertIn("{r.status}", page)
        # Her iki liste de aynı durum satırını taşımalı; kayıt sayısı kadar
        # görünür olmalı.
        self.assertEqual(
            page.count("<span className=\"tag\">{r.status}</span>"),
            2,
            "görsel ve kontrol bölümlerinin ikisi de durum etiketi göstermeli",
        )

    def test_mineru_output_is_labelled_non_authoritative(self):
        for r in self.doc["records"]:
            with self.subTest(question=r["question"]["question_number"]):
                mineru = r["mineru_comparison"]
                self.assertIsNotNone(mineru)
                self.assertFalse(mineru["authoritative"])


if __name__ == "__main__":
    unittest.main()