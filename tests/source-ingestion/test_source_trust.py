import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/source-ingestion"))

from download_official_pdfs import DiscoveredPdf, download_pdf
from create_ingestion_manifest import create_manifest
from source_trust import validate_discovered_pdf, validate_pdf_redirect


class FakeResponse:
    def __init__(self, body=b"%PDF-1.7\npilot", url="https://cdn.eba.gov.tr/pilot.pdf", content_type="application/pdf"):
        self.body = body
        self.url = url
        self.headers = {"Content-Type": content_type}
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self.url

    def read(self, size=-1):
        if self.offset >= len(self.body):
            return b""
        chunk = self.body[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


class FakeOpener:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def open(self, request, timeout=0):
        self.calls += 1
        return self.response


def discovered(pdf_url="https://cdn.eba.gov.tr/pilot.pdf"):
    return DiscoveredPdf(
        source_id="MEB-LGS-2025",
        discovered_from="https://odsgm.meb.gov.tr/registry",
        source_page_url="https://odsgm.meb.gov.tr/registry",
        pdf_url=pdf_url,
        discovery_redirect_chain=["https://odsgm.meb.gov.tr/registry"],
        anchor_text="Sayısal Bölüm A Kitapçığı",
    )


class SourceTrustTests(unittest.TestCase):
    def test_official_page_discovered_cdn_pdf_is_accepted(self):
        validate_discovered_pdf(discovered())

    def test_random_cdn_url_is_rejected_before_network_use(self):
        with self.assertRaisesRegex(ValueError, "discovery evidence"):
            validate_discovered_pdf("https://cdn.eba.gov.tr/random.pdf")

    def test_cdn_to_foreign_redirect_and_http_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "redirect"):
            validate_pdf_redirect("https://cdn.eba.gov.tr/pilot.pdf", "https://attacker.example/payload.pdf")
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            validate_pdf_redirect("https://cdn.eba.gov.tr/pilot.pdf", "http://cdn.eba.gov.tr/pilot.pdf")

    def test_pdf_download_records_integrity_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "pilot.pdf"
            body = b"%PDF-1.7\npilot"
            result = download_pdf(discovered(), destination, FakeOpener(FakeResponse(body=body)))
        self.assertEqual(result["sha256"], hashlib.sha256(body).hexdigest())
        self.assertEqual(result["content_type"], "application/pdf")
        self.assertEqual(result["size_bytes"], len(body))
        self.assertEqual(result["final_url"], "https://cdn.eba.gov.tr/pilot.pdf")
        self.assertEqual(result["redirect_chain"], ["https://cdn.eba.gov.tr/pilot.pdf"])

    def test_html_and_bad_pdf_magic_are_rejected_without_archive(self):
        for body, content_type, message in (
            (b"<html>not a pdf</html>", "text/html", "Content-Type"),
            (b"not-a-pdf", "application/pdf", "PDF signature"),
        ):
            with self.subTest(content_type=content_type), tempfile.TemporaryDirectory() as directory:
                destination = Path(directory) / "pilot.pdf"
                with self.assertRaisesRegex(ValueError, message):
                    download_pdf(discovered(), destination, FakeOpener(FakeResponse(body=body, content_type=content_type)))
                self.assertFalse(destination.exists())

    def test_manifest_keeps_discovery_chain_and_separates_rights_review(self):
        source = {
            "id": "MEB-LGS-2025",
            "type": "REAL_LGS",
            "year": 2025,
            "official_index_url": "https://odsgm.meb.gov.tr/registry",
        }
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / "pilot.pdf"
            result = download_pdf(discovered(), pdf, FakeOpener(FakeResponse()))
            manifest = create_manifest(pdf, source, result)
        for field in ("source_page_url", "discovered_from", "pdf_url", "final_url", "source_id", "sha256", "content_type", "size_bytes", "redirect_chain"):
            self.assertIn(field, manifest)
        self.assertEqual(manifest["status"], "NEEDS_REVIEW")
        self.assertEqual(manifest["provenance_status"], "DISCOVERED")
        self.assertEqual(manifest["usage_rights_review"], "UNREVIEWED")


if __name__ == "__main__":
    unittest.main()
