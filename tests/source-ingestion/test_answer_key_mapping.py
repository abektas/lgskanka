#!/usr/bin/env python3
"""T5.8 testleri: resmi cevap anahtarının (subject, question_number) ile eşleştirilmesi.

Cevap yalnızca resmî PDF'teki cevap-anahtarı kanıtından gelir; model tahmini,
soru çözümü veya OCR kullanılmaz. Eşleme konusuz yapılmaz.
"""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "source-ingestion"))

from extract_pdf_candidates import extract, parse_answer_key  # noqa: E402

REAL_PDF = ROOT / "scripts/source-ingestion/data/questions/archive/MEB-LGS-2022/01-2022_sayisal_bolum_a_kitapcigi_ve_cevap_anahtari.pdf"
REAL_SHA = "8a1c6526b50b4b695dd6f48bfce42c7fbed53d26f0057e554f666cb4682c4142"
REAL_MANIFEST = ROOT / "scripts/source-ingestion/data/questions/manifests/MEB-LGS-2022__8a1c6526b50b.json"
QUARANTINE_PDF = ROOT / "scripts/source-ingestion/data/questions/archive/MEB-LGS-2022/24220837_alte_fullmembershipcertificate.pdf"
QUARANTINE_MANIFEST = ROOT / "scripts/source-ingestion/data/questions/manifests/MEB-LGS-2022__cf9b2e3069eb.json"
SOURCE = {
    "id": "MEB-LGS-2022",
    "type": "REAL_LGS",
    "year": 2022,
    "official_index_url": "https://odsgm.meb.gov.tr/www/5-haziran-2022-tarihinde-yapilan-sinavla-ogrenci-alacak-ortaogretim-kurumlarina-iliskin-merkezi-sinavin-soru-kitapciklari-ve-cevap-anahtarlari/icerik/822",
}


def page(number, text):
    return {"page": number, "text": text}


def key_page(page_no=33, first="1.   D\n2.   A\n3.   B\n", second="1.   D\n2.   B\n"):
    """MEB satır düzeni: cevap bloğu, etiketin ALTINDA yer alır."""
    return page(page_no, '"A" KİTAPÇIĞI CEVAP ANAHTARI\n' + first + "MATEMATİK\n" + second + "FEN BİLİMLERİ\n")


class SubjectAwareAnswerKeyTest(unittest.TestCase):
    def test_row_caption_layout_attributes_block_to_label_below(self):
        parsed = parse_answer_key([key_page()])
        self.assertEqual(parsed["by_subject"]["MATEMATİK"][1]["letter"], "D")
        self.assertEqual(parsed["by_subject"]["MATEMATİK"][2]["letter"], "A")
        self.assertEqual(parsed["by_subject"]["FEN BİLİMLERİ"][2]["letter"], "B")

    def test_same_number_in_two_subjects_is_independent(self):
        parsed = parse_answer_key([key_page(first="1.   D\n2.   A\n", second="1.   C\n2.   B\n")])
        self.assertEqual(parsed["by_subject"]["MATEMATİK"][1]["letter"], "D")
        self.assertEqual(parsed["by_subject"]["FEN BİLİMLERİ"][1]["letter"], "C")

    def test_question_20_maps_to_its_own_subject(self):
        parsed = parse_answer_key([key_page(first="20.   B\n", second="20.   D\n")])
        self.assertEqual(parsed["by_subject"]["MATEMATİK"][20]["letter"], "B")
        self.assertEqual(parsed["by_subject"]["FEN BİLİMLERİ"][20]["letter"], "D")

    def test_block_without_subject_label_is_not_mapped(self):
        parsed = parse_answer_key([page(33, "CEVAP ANAHTARI\n1.   D\n2.   A\n")])
        self.assertNotIn("MATEMATİK", parsed["by_subject"])
        self.assertEqual(parsed["by_subject"], {})
        self.assertTrue(parsed["diagnostics"])

    def test_unknown_subject_label_is_rejected(self):
        parsed = parse_answer_key([page(33, "CEVAP ANAHTARI\n1.   D\nEDEBİYAT\n2.   A\n")])
        self.assertEqual(parsed["by_subject"], {})

    def test_duplicate_pair_in_same_block_is_rejected(self):
        parsed = parse_answer_key([key_page(first="1.   D\n1.   C\n", second="1.   D\n")])
        self.assertNotIn("MATEMATİK", parsed["by_subject"])
        self.assertTrue(any("duplicate" in reason for reason in parsed["diagnostics"]))

    def test_two_blocks_mapped_to_same_subject_are_ambiguous(self):
        text = "CEVAP ANAHTARI\n1.   D\nMATEMATİK\n2.   A\nMATEMATİK\n3.   B\n"
        parsed = parse_answer_key([page(33, text)])
        self.assertNotIn("MATEMATİK", parsed["by_subject"])

    def test_evidence_records_page_and_source(self):
        parsed = parse_answer_key([key_page(page_no=33)])
        entry = parsed["by_subject"]["MATEMATİK"][1]
        self.assertEqual(entry["page"], 33)
        self.assertIn("CEVAP ANAHTARI", entry["evidence"])

    def test_page_without_answer_key_marker_is_ignored(self):
        parsed = parse_answer_key([page(2, "1. Bu testte 20 soru vardır.\nA) 1  B) 2  C) 3  D) 4\n")])
        self.assertEqual(parsed["by_subject"], {})
@unittest.skipUnless(REAL_PDF.is_file(), "gerçek MEB PDF'i arşivde bulunamadı")
class RealAnswerKeyIntegrationTest(unittest.TestCase):
    """Gerçek 2022 SAYISAL kitapçığında uçtan uca eşleme ölçümü."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(REAL_MANIFEST.read_text(encoding="utf-8"))
        cls.result = extract(REAL_PDF, SOURCE, cls.manifest["source_file_url"], "SAYISAL", cls.manifest)
        cls.by_key = {
            (r["question"]["subject"], r["source"]["question_number"]): r for r in cls.result["records"]
        }

    def test_pdf_is_the_official_pilot_file(self):
        self.assertEqual(hashlib.sha256(REAL_PDF.read_bytes()).hexdigest(), REAL_SHA)

    def test_candidate_count_preserved_from_t57(self):
        self.assertEqual(self.result["candidate_count"], 34)

    def test_answer_key_evidence_is_page_33(self):
        mapped = [r for r in self.result["records"] if r["extraction"].get("answer_key_map")]
        self.assertTrue(mapped)
        for record in mapped:
            with self.subTest(record=record["id"]):
                self.assertEqual(record["extraction"]["answer_key_map"]["page"], 33)

    def test_both_subjects_have_twenty_official_answers(self):
        counts = self.result["answer_key_summary"]["counts"]
        self.assertEqual(counts.get("MATEMATİK"), 20)
        self.assertEqual(counts.get("FEN BİLİMLERİ"), 20)

    def test_mathematics_question_01_matches_official_key(self):
        self.assertEqual(self.by_key[("MATEMATİK", 1)]["answer_key"]["candidate"], "D")

    def test_science_question_01_is_mapped_independently(self):
        record = self.by_key[("FEN BİLİMLERİ", 1)]
        self.assertEqual(record["answer_key"]["candidate"], "D")
        self.assertEqual(record["question"]["subject"], "FEN BİLİMLERİ")

    def test_question_20_differs_between_subjects(self):
        # Sayfa 33: Matematik 20 = B, Fen Bilimleri 20 = D
        self.assertEqual(self.by_key[("MATEMATİK", 20)]["answer_key"]["candidate"], "B")
        self.assertEqual(self.by_key[("FEN BİLİMLERİ", 20)]["answer_key"]["candidate"], "D")

    def test_every_candidate_is_mapped_once(self):
        for record in self.result["records"]:
            with self.subTest(record=record["id"]):
                self.assertIsNotNone(record["answer_key"]["candidate"])
                mapping = record["extraction"]["answer_key_map"]
                self.assertEqual(mapping["subject"], record["question"]["subject"])
                self.assertEqual(mapping["question_number"], record["source"]["question_number"])

    def test_no_candidate_takes_another_subject_answer(self):
        summary = self.result["answer_key_summary"]
        self.assertEqual(summary["subject_conflicts"], 0)
        self.assertEqual(summary["unmapped_candidates"], 0)

    def test_missing_mathematics_questions_do_not_break_key(self):
        # Matematik 4, 10, 11, 12, 14, 19 çıkarılamıyor; anahtar yine bütün olmalı.
        self.assertEqual(self.result["answer_key_summary"]["counts"]["MATEMATİK"], 20)
        self.assertEqual(self.result["candidate_count"], 34)

    def test_orphan_answers_create_no_question_records(self):
        numbers = {n for (s, n) in self.by_key if s == "MATEMATİK"}
        self.assertNotIn(4, numbers, "çıkarılamayan soru için sahte kayıt üretilmemeli")
        self.assertEqual(len(self.by_key), 34)

    def test_mapping_never_writes_the_answer_field(self):
        for record in self.result["records"]:
            with self.subTest(record=record["id"]):
                self.assertIsNone(record["answer_key"]["answer"])
                self.assertFalse(record["answer_key"]["answer_key_verified"])
                self.assertEqual(record["answer_key"]["authority"], "OFFICIAL_MEB_ONLY")

    def test_mapping_never_verifies_or_publishes(self):
        self.assertEqual(self.result["status"], "NEEDS_REVIEW")
        self.assertFalse(self.result["published"])
        for record in self.result["records"]:
            self.assertEqual(record["status"], "NEEDS_REVIEW")

    def test_provenance_chain_is_recorded(self):
        mapping = self.by_key[("MATEMATİK", 1)]["extraction"]["answer_key_map"]
        self.assertEqual(mapping["source_id"], "MEB-LGS-2022")
        self.assertEqual(mapping["booklet"], "SAYISAL")
        self.assertEqual(mapping["source_sha256"], REAL_SHA)
        self.assertIn("CEVAP ANAHTARI", mapping["evidence"])


@unittest.skipUnless(QUARANTINE_PDF.is_file(), "karantina artifact'ı bulunamadı")
class QuarantineTwinTest(unittest.TestCase):
    """T5.6 karantina davranışı bozulmamalı."""

    def test_quarantined_pdf_cannot_be_mapped(self):
        from extract_pdf_candidates import validate_manifest_for_pdf

        quarantined = json.loads(QUARANTINE_MANIFEST.read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            validate_manifest_for_pdf(quarantined, SOURCE, QUARANTINE_PDF)


if __name__ == "__main__":
    unittest.main()