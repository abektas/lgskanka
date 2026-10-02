#!/usr/bin/env python3
"""T5.7 testleri: gerçek MEB LGS 2022 kitapçığından soru ayrıştırma.

Kapsam yalnızca soru segmentation/extraction'dır: answer-key parser,
müfredat eşleme, çözüm üretimi ve doğrulama kapıları değiştirilmez.
"""
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "source-ingestion"))

from extract_pdf_candidates import (  # noqa: E402
    extract,
    parse_options,
    segment_lines,
)
from validate_source_registry import official_host  # noqa: E402

REAL_PDF = ROOT / "scripts/source-ingestion/data/questions/archive/MEB-LGS-2022/01-2022_sayisal_bolum_a_kitapcigi_ve_cevap_anahtari.pdf"
REAL_SHA = "8a1c6526b50b4b695dd6f48bfce42c7fbed53d26f0057e554f666cb4682c4142"
QUARANTINE_PDF = ROOT / "scripts/source-ingestion/data/questions/archive/MEB-LGS-2022/24220837_alte_fullmembershipcertificate.pdf"
REAL_MANIFEST = ROOT / "scripts/source-ingestion/data/questions/manifests/MEB-LGS-2022__8a1c6526b50b.json"
QUARANTINE_MANIFEST = ROOT / "scripts/source-ingestion/data/questions/manifests/MEB-LGS-2022__cf9b2e3069eb.json"
SOURCE = {
    "id": "MEB-LGS-2022",
    "type": "REAL_LGS",
    "year": 2022,
    "official_index_url": "https://odsgm.meb.gov.tr/www/5-haziran-2022-tarihinde-yapilan-sinavla-ogrenci-alacak-ortaogretim-kurumlarina-iliskin-merkezi-sinavin-soru-kitapciklari-ve-cevap-anahtarlari/icerik/822",
}


class OptionParsingTest(unittest.TestCase):
    """Seçenekler bu kitapçıkta çoğunlukla tek satırda ve araya boşlukla giriyor."""

    def test_single_line_options_are_parsed(self):
        options = parse_options("Soru metni?\nA) 8  B) 6  C) 25  D) 10")
        self.assertEqual(sorted(options), ["A", "B", "C", "D"])
        self.assertEqual(options["C"], "25")

    def test_multi_line_options_are_parsed(self):
        options = parse_options("A) birinci\nB) ikinci\nC) üçüncü\nD) dördüncü")
        self.assertEqual(sorted(options), ["A", "B", "C", "D"])

    def test_incomplete_option_set_is_not_invented(self):
        self.assertLess(len(parse_options("A) sadece bir\nC) üçüncü")), 4)

    def test_text_without_options_returns_empty(self):
        self.assertEqual(parse_options("1. Bu testte 20 soru vardır."), {})
class SegmentationTest(unittest.TestCase):
    """Sınav talimatı, cevap anahtarı ve alt maddeler soru sayılmamalı."""

    def blocks(self, text):
        # Sentetik örneklerde ders başlığı yok; üretim akışındaki varsayılan
        # korumayı (ön kısım eleme) devre dışı bırakarak yalnız segmentasyonu sınar.
        return segment_lines(
            [(1, None, line) for line in text.splitlines()],
            require_subject_header=False,
        )

    def test_exam_instructions_are_not_questions(self):
        blocks = self.blocks(
            "1. Bu testte 20 soru vardır.\n"
            "2. Cevaplarınızı, cevap kâğıdına işaretleyiniz.\n"
            "MATEMATİK\n"
            "1.   Gerçek bir soru metni burada yer alıyor ve yeterince uzundur.\n"
            "A) 1  B) 2  C) 3  D) 4\n"
        )
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["question_number"], 1)
        self.assertIn("Gerçek bir soru", blocks[0]["stem"])

    def test_answer_key_lines_are_not_questions(self):
        self.assertEqual(self.blocks("CEVAP ANAHTARI\n1.   D\n2.   A\n3.   B\n"), [])

    def test_sub_items_do_not_split_a_question(self):
        blocks = self.blocks(
            "19.   Bir deneyde şekildeki kaplara sıvı konulmuştur ve sonuçlar şöyledir.\n"
            "1.   kaptaki sıvının sıcaklığı ölçülmüştür.\n"
            "2.   kaptaki sıvının hacmi kaydedilmiştür.\n"
            "A) 1  B) 2  C) 3  D) 4\n"
        )
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["question_number"], 19)

    def test_subject_is_tracked_across_pages(self):
        lines = [
            (1, None, "FEN BİLİMLERİ"),
            (1, None, "1.   Fen bilimleri sorusu ve yeterince uzun bir açıklama metni."),
            (1, None, "A) 1  B) 2  C) 3  D) 4"),
        ]
        blocks = segment_lines(lines)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["subject"], "FEN BİLİMLERİ")

@unittest.skipUnless(REAL_PDF.is_file(), "gerçek MEB PDF'i arşivde bulunamadı")
class RealBookletExtractionTest(unittest.TestCase):
    """Gerçek 2022 SAYISAL kitapçığı üzerinde uçtan uca ölçüm."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(REAL_MANIFEST.read_text(encoding="utf-8"))
        cls.result = extract(REAL_PDF, SOURCE, cls.manifest["source_file_url"], "SAYISAL", cls.manifest)

    def test_pdf_hash_matches_the_official_pilot(self):
        self.assertEqual(hashlib.sha256(REAL_PDF.read_bytes()).hexdigest(), REAL_SHA)
        self.assertEqual(self.result["source_sha256"], REAL_SHA)

    def test_candidates_are_far_fewer_than_before(self):
        # T5.5 ölçümü: 111 aday (40 gerçek soru). Talimat/anahtar gürültüsü giderilmeli.
        self.assertLess(self.result["candidate_count"], 50)

    def test_every_candidate_is_either_complete_or_explicitly_flagged(self):
        """Dört seçenekli ya da uyarıyla işaretlenmiş olmalı; bozuk seçenek sessizce geçmez."""
        for record in self.result["records"]:
            options = record["question"]["options"]
            warnings = record["extraction"]["warnings"]
            with self.subTest(record=record["id"]):
                if sorted(options) != ["A", "B", "C", "D"]:
                    self.assertTrue(
                        warnings,
                        f"{record['id']} eksik seçenekli ama uyarısız: {sorted(options)}",
                    )

    def test_option_boundaries_are_flagged_when_marker_inside_option(self):
        for record in self.result["records"]:
            options = record["question"]["options"]
            for value in options.values():
                if re.search(r"(?<![A-Za-z0-9ÇĞİÖŞÜçğıöşü])[A-D]\s*\)\s", value):
                    with self.subTest(record=record["id"]):
                        self.assertIn("option_boundary_ambiguous", record["extraction"]["warnings"])

    def test_flagged_candidates_are_never_low_confidence(self):
        for record in self.result["records"]:
            with self.subTest(record=record["id"]):
                if record["extraction"]["warnings"]:
                    self.assertEqual(record["extraction"]["confidence"], "LOW")

    def test_every_candidate_has_stem_and_subject(self):
        for record in self.result["records"]:
            with self.subTest(record=record["id"]):
                self.assertGreaterEqual(len(record["question"]["stem"]), 40)
                self.assertTrue(record["question"]["subject"])

    def test_question_numbers_are_in_expected_range(self):
        for record in self.result["records"]:
            with self.subTest(record=record["id"]):
                self.assertGreaterEqual(record["source"]["question_number"], 1)
                self.assertLessEqual(record["source"]["question_number"], 20)

    def test_no_duplicate_record_ids(self):
        ids = [record["id"] for record in self.result["records"]]
        self.assertEqual(len(ids), len(set(ids)), "Matematik ve Fen soruları çakışmamalı")

    def test_no_duplicate_subject_and_number(self):
        keys = [(r["question"]["subject"], r["source"]["question_number"]) for r in self.result["records"]]
        self.assertEqual(len(keys), len(set(keys)))

    def test_candidate_pages_are_monotonic(self):
        for record in self.result["records"]:
            with self.subTest(record=record["id"]):
                self.assertLessEqual(record["question"]["page_start"], record["question"]["page_end"])

    def test_exam_instructions_are_not_candidates(self):
        stems = " ".join(r["question"]["stem"] for r in self.result["records"])
        self.assertNotIn("Salon yoklama", stems)
        self.assertNotIn("Bu testte 20 soru vardır", stems)

    def test_answer_key_page_is_not_a_candidate(self):
        pages = {r["question"]["page_end"] for r in self.result["records"]}
        self.assertNotIn(33, pages, "cevap anahtarı sayfası aday üretmemeli")

    def test_nothing_is_auto_verified(self):
        for record in self.result["records"]:
            with self.subTest(record=record["id"]):
                self.assertEqual(record["status"], "NEEDS_REVIEW")
                self.assertFalse(any(record["checks"].values()))
                self.assertIsNone(record["answer_key"]["answer"])

    def test_output_is_never_published(self):
        self.assertEqual(self.result["status"], "NEEDS_REVIEW")
        self.assertFalse(self.result["published"])

    def test_answer_key_candidates_remain_for_later_mapping(self):
        # T5.8 cevap anahtarını (subject, question_number) ile eşleştirecek.
        self.assertIn("answer_key_candidates", self.result["records"][0]["extraction"])

    def test_both_subjects_are_detected(self):
        subjects = {r["question"]["subject"] for r in self.result["records"]}
        self.assertIn("MATEMATİK", subjects)
        self.assertIn("FEN BİLİMLERİ", subjects)

    def test_confidence_is_within_canonical_enum(self):
        for record in self.result["records"]:
            with self.subTest(record=record["id"]):
                self.assertIn(record["extraction"]["confidence"], {"LOW", "UNREVIEWED", "HUMAN_REVIEWED"})

    def test_clean_candidates_are_not_flagged_low_confidence(self):
        """Uyarısız ve tam dört seçenekli adaylar UNREVIEWED olmalı (VERIFIED değil)."""
        clean = [
            r for r in self.result["records"]
            if sorted(r["question"]["options"]) == ["A", "B", "C", "D"] and not r["extraction"]["warnings"]
        ]
        self.assertTrue(clean)
        for record in clean:
            with self.subTest(record=record["id"]):
                self.assertEqual(record["extraction"]["confidence"], "UNREVIEWED")
                self.assertEqual(record["status"], "NEEDS_REVIEW")
                self.assertIsNone(record["answer_key"]["answer"])


@unittest.skipUnless(QUARANTINE_PDF.is_file(), "karantina artifact'ı bulunamadı")
class QuarantineStillBlockedTest(unittest.TestCase):
    """T5.6 davranışı bozulmamalı: karantinaya alınmış artifact işlenemez."""

    def test_quarantined_manifest_is_refused(self):
        from extract_pdf_candidates import validate_manifest_for_pdf

        quarantined = json.loads(QUARANTINE_MANIFEST.read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            validate_manifest_for_pdf(quarantined, SOURCE, QUARANTINE_PDF)

    def test_registry_urls_stay_official(self):
        registry = json.loads((ROOT / "data/source-engine/config/source-registry.json").read_text(encoding="utf-8"))
        for row in registry["sources"]:
            with self.subTest(source=row["id"]):
                self.assertTrue(official_host(row["official_index_url"].split("/")[2].lower()))


if __name__ == "__main__":
    unittest.main()
    def test_page_numbers_are_not_questions(self):
        self.assertEqual(self.blocks("2\n18\nMATEMATİK\n"), [])