import copy
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/source-ingestion"))
from build_review_queue import build, fingerprint
from extract_pdf_candidates import extract, segment_page
from validate_canonical import REQUIRED_CHECKS, transition, validate_record
from publish_verified import publish
from download_official_pdfs import DiscoveredPdf, resolve_pdfs, download_pdf, select_discoveries
from extract_pdf_candidates import validate_manifest_for_pdf


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "schema_version": "1.0", "id": "MEB-LGS-2025:SAYISAL_A:Q01",
            "source": {"source_id": "MEB-LGS-2025", "source_type": "REAL_LGS", "year": 2025,
                       "official_index_url": "https://odsgm.meb.gov.tr/www/", "source_file_url": "https://meb.gov.tr/a.pdf",
                       "source_page_url": "https://odsgm.meb.gov.tr/www/", "discovered_from": "https://odsgm.meb.gov.tr/www/",
                       "pdf_url": "https://meb.gov.tr/a.pdf", "final_url": "https://meb.gov.tr/a.pdf",
                       "redirect_chain": ["https://meb.gov.tr/a.pdf"],
                       "source_sha256": hashlib.sha256(b"pdf").hexdigest(), "booklet": "SAYISAL_A", "question_number": 1},
            "question": {"grade": 8, "subject": "Matematik", "stem": "Bu yeterince uzun bir örnek soru köküdür.", "options": {"A":"1", "B":"2", "C":"3", "D":"4"}, "page_start": 2, "page_end": 2},
            "answer_key": {"candidate": "C", "answer": "C", "authority": "OFFICIAL_MEB_ONLY", "source_verified": True, "answer_key_verified": True},
            "curriculum": {"LGS_REFERENCE_2018_PLUS": {"status":"VERIFIED", "version":"2018+", "subject":"Matematik", "unit":"Üçgenler", "topic":"Açı ilişkileri", "learning_outcome":"Kanıt destekli kazanım", "skill":"Çıkarım", "evidence_url":"https://meb.gov.tr/cur.pdf"}, "CURRENT_TYMM": {"status":"UNMAPPED", "version":None, "subject":None, "unit":None, "topic":None, "learning_outcome":None, "skill":None, "evidence_url":None}},
            "extraction": {"method":"pypdf-text-v1", "retrieved_at":"2026-09-30T00:00:00+00:00", "confidence":"HUMAN_REVIEWED", "warnings":[], "answer_key_candidates":[]},
            "solution": "Adım adım açıklama.", "status":"NEEDS_REVIEW", "checks": {key: True for key in REQUIRED_CHECKS}
        }

    def test_extraction_segmentation_flags_uncertainty_and_schema_fields(self):
        rows = segment_page("1. Bu yeterince uzun soru metnidir?\nA) Bir\nB) İki\nC) Üç\nD) Dört", 7)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["page_start"], 7)
        self.assertEqual(rows[0]["extraction_warnings"], [])
        self.assertEqual(set(rows[0]["options"]), {"A", "B", "C", "D"})
        uncertain = segment_page("1. kısa\nA) A", 1)[0]
        self.assertIn("low_text_density_or_scanned_content", uncertain["extraction_warnings"])

    def test_answer_key_and_source_checks_are_independent(self):
        row = copy.deepcopy(self.record)
        row["checks"]["answer_key_source_verified"] = False
        self.assertTrue(any("answer_key_source_verified" in error for error in validate_record(row, require_verified=True)))
        row = copy.deepcopy(self.record)
        row["answer_key"]["source_verified"] = False
        self.assertTrue(any("answer-key source" in error for error in validate_record(row, require_verified=True)))
        row = copy.deepcopy(self.record)
        row["answer_key"]["answer"] = None
        self.assertTrue(any("canonical answer" in error for error in validate_record(row, require_verified=True)))

    def test_year_policy_and_url_policy(self):
        row = copy.deepcopy(self.record)
        row["source"]["year"] = 2017
        self.assertTrue(any("2018 or later" in error for error in validate_record(row, require_verified=True)))
        row = copy.deepcopy(self.record)
        row["source"]["source_file_url"] = "https://meb.gov.tr.attacker.example/a.pdf"
        row["source"]["pdf_url"] = "https://meb.gov.tr.attacker.example/a.pdf"
        row["source"]["final_url"] = "https://meb.gov.tr.attacker.example/a.pdf"
        row["source"]["redirect_chain"] = ["https://meb.gov.tr.attacker.example/a.pdf"]
        self.assertTrue(any("PDF URL" in error for error in validate_record(row, require_verified=True)))

    def test_status_transitions_require_all_checks_and_verified_is_gated(self):
        row = copy.deepcopy(self.record)
        row["checks"]["source_verified"] = False
        with self.assertRaisesRegex(ValueError, "verification gate failed"):
            transition(row, "VERIFIED")
        verified = transition(self.record, "VERIFIED")
        self.assertEqual(verified["status"], "VERIFIED")
        with self.assertRaisesRegex(ValueError, "only NEEDS_REVIEW"):
            transition(verified, "VERIFIED")

    def test_duplicate_fingerprint_matches_nested_canonical_shape(self):
        a = {"question": {"stem":"  ayni metin ", "options":{"A":"1","B":"2","C":"3","D":"4"}}}
        b = {"question": {"stem":"AYNI   METIN", "options":{"A":"1","B":"2","C":"3","D":"4"}}}
        self.assertEqual(fingerprint(a), fingerprint(b))
        queue = build({"records": [{"id":"q1", **a}, {"id":"q2", **b}]})
        self.assertEqual(queue["items"][0]["possible_duplicate_indices"], [1])
        self.assertFalse(queue["items"][0]["checks"]["answer_key_source_verified"])

    def test_only_verified_records_are_promoted_and_answer_stays_private_to_api_store(self):
        row = copy.deepcopy(self.record)
        payload = {"records": [row]}
        api_rows = publish(payload)
        self.assertEqual(api_rows, [])
        row["status"] = "VERIFIED"
        api_rows = publish(payload)
        self.assertEqual(len(api_rows), 1)
        self.assertEqual(api_rows[0]["answer"], "C")
        self.assertTrue(api_rows[0]["verification"]["answer_key_source_verified"])
        broken = copy.deepcopy(row)
        broken["checks"]["answer_key_verified"] = False
        with self.assertRaisesRegex(ValueError, "refusing malformed VERIFIED"):
            publish({"records": [broken]})
        duplicate = copy.deepcopy(row); duplicate["id"] = "MEB-LGS-2025:SAYISAL_A:Q99"
        with self.assertRaisesRegex(ValueError, "duplicate VERIFIED records"):
            publish({"records": [row, duplicate]})


    def test_downloader_uses_registered_page_context_and_accepts_discovered_cdn_pdfs(self):
        class FakeResponse:
            def __init__(self, body): self.body = body
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def geturl(self): return "https://odsgm.meb.gov.tr/index"
            def read(self, size=-1): return self.body[:size]
        class FakeOpener:
            def open(self, request, timeout=0): return FakeResponse(b"""<a href='/meb_iys_dosyalar/certificate.pdf'></a>
                <p>Sozel Bolum A Kitapcigi icin <a href='https://cdn.eba.gov.tr/a.pdf'>tiklayiniz</a></p>
                <p>Sayisal A kitapcigi <a href='/meb_iys_dosyalar/booklet.pdf'>PDF</a></p>""")
        source = {"id":"MEB-LGS-2025", "official_index_url":"https://odsgm.meb.gov.tr/index"}
        found, skipped = resolve_pdfs(source, FakeOpener())
        self.assertEqual([item.pdf_url for item in found], [
            "https://cdn.eba.gov.tr/a.pdf",
            "https://odsgm.meb.gov.tr/meb_iys_dosyalar/booklet.pdf",
        ])
        self.assertEqual(found[0].source_page_url, source["official_index_url"])
        self.assertEqual(found[0].discovered_from, source["official_index_url"])
        self.assertEqual(skipped, [])

    def test_booklet_selection_uses_official_anchor_text(self):
        rows = [
            DiscoveredPdf("MEB-LGS-2025", "https://odsgm.meb.gov.tr/index", "https://odsgm.meb.gov.tr/index", "https://cdn.eba.gov.tr/sozel.pdf", ["https://odsgm.meb.gov.tr/index"], "Sözel Bölüm A Kitapçığı"),
            DiscoveredPdf("MEB-LGS-2025", "https://odsgm.meb.gov.tr/index", "https://odsgm.meb.gov.tr/index", "https://cdn.eba.gov.tr/sayisal.pdf", ["https://odsgm.meb.gov.tr/index"], "Sayısal Bölüm A Kitapçığı"),
        ]
        self.assertEqual([row.pdf_url for row in select_discoveries(rows, "SAYISAL_A")], ["https://cdn.eba.gov.tr/sayisal.pdf"])


    def test_manifest_hash_must_match_before_extraction(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            pdf=Path(directory)/"source.pdf"; pdf.write_bytes(b"%PDF-1.4\npilot")
            row=copy.deepcopy(self.record["source"])
            row.update({
                "source_page_url": row["official_index_url"],
                "discovered_from": row["official_index_url"],
                "pdf_url": "https://cdn.eba.gov.tr/source.pdf",
                "final_url": "https://cdn.eba.gov.tr/source.pdf",
                "source_file_url": "https://cdn.eba.gov.tr/source.pdf",
                "redirect_chain": ["https://cdn.eba.gov.tr/source.pdf"],
                "discovery_redirect_chain": [row["official_index_url"]],
                "content_type": "application/pdf",
                "size_bytes": pdf.stat().st_size,
                "provenance_status": "DISCOVERED",
                "usage_rights_review": "UNREVIEWED",
            })
            row["sha256"]=hashlib.sha256(pdf.read_bytes()).hexdigest()
            row["status"]="NEEDS_REVIEW"; row["published"]=False
            self.assertEqual(validate_manifest_for_pdf(row, {"id":"MEB-LGS-2025", "official_index_url":row["official_index_url"]}, pdf), row["source_file_url"])
            row["sha256"]="0"*64
            with self.assertRaisesRegex(ValueError, "hash/status"):
                validate_manifest_for_pdf(row, {"id":"MEB-LGS-2025", "official_index_url":row["official_index_url"]}, pdf)

    def test_empty_text_extraction_is_explicit_needs_review(self):
        source = {"id": "MEB-LGS-2025", "type": "REAL_LGS", "year": 2025, "official_index_url": "https://odsgm.meb.gov.tr/registry"}
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / "scanned.pdf"
            pdf.write_bytes(b"%PDF-1.4\nscanned")
            with patch("extract_pdf_candidates.extract_text", return_value=[{"page": 1, "text": ""}]):
                result = extract(pdf, source, "https://cdn.eba.gov.tr/scanned.pdf", "SAYISAL")
        self.assertEqual(result["status"], "NEEDS_REVIEW")
        self.assertEqual(result["candidate_count"], 0)
        self.assertIn("no_extractable_text_or_scanned_pdf", result["review_reasons"])
        self.assertFalse(result["published"])

    def test_pdf_archive_is_idempotent_and_refuses_changed_bytes(self):
        class FakeResponse:
            def __init__(self, body): self.body=body; self.offset=0; self.headers={"Content-Type":"application/pdf"}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def geturl(self): return "https://odsgm.meb.gov.tr/source.pdf"
            def read(self, size=-1):
                if self.offset >= len(self.body): return b""
                chunk=self.body[self.offset:self.offset+size]; self.offset+=len(chunk); return chunk
        class FakeOpener:
            def __init__(self, body): self.body=body
            def open(self, request, timeout=0): return FakeResponse(self.body)
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            dest=Path(directory)/"source.pdf"; data=b"%PDF-1.4\noriginal"
            discovery = DiscoveredPdf(
                source_id="MEB-LGS-2025", discovered_from="https://odsgm.meb.gov.tr/index",
                source_page_url="https://odsgm.meb.gov.tr/index", pdf_url="https://odsgm.meb.gov.tr/source.pdf",
                discovery_redirect_chain=["https://odsgm.meb.gov.tr/index"], anchor_text="Kitapçık",
            )
            first=download_pdf(discovery, dest, FakeOpener(data))
            second=download_pdf(discovery, dest, FakeOpener(data))
            self.assertEqual(first["sha256"], second["sha256"])
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                download_pdf(discovery, dest, FakeOpener(b"%PDF-1.4\nchanged"))
            self.assertEqual(dest.read_bytes(), data)

    def test_schema_represents_both_layers_and_distinct_answer_flags(self):
        schema = json.loads((ROOT / "scripts/source-ingestion/canonical_schema.json").read_text())
        self.assertIn("LGS_REFERENCE_2018_PLUS", schema["properties"]["curriculum"]["properties"])
        self.assertIn("CURRENT_TYMM", schema["properties"]["curriculum"]["properties"])
        answer_props = schema["properties"]["answer_key"]["properties"]
        self.assertIn("source_verified", answer_props)
        self.assertIn("answer_key_verified", answer_props)
        source_props = schema["properties"]["source"]["properties"]
        self.assertIn("source_page_url", source_props)
        self.assertIn("discovered_from", source_props)
        self.assertIn("redirect_chain", source_props)

if __name__ == "__main__": unittest.main()
