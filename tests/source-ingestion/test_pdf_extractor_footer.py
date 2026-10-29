#!/usr/bin/env python3
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "source-ingestion"))

from nuli_qbank_pdf_extractor import QuestionAnchor, make_crop_records  # noqa: E402


class FooterBoundaryTest(unittest.TestCase):
    def test_crop_ends_before_source_page_footer(self):
        page = SimpleNamespace(height=841.89)
        anchor = QuestionAnchor(
            number=13,
            x0=28.3,
            top=44.7,
            x1=36.7,
            bottom=55.0,
            column=0,
            confidence=0.85,
            text="13.",
        )

        records = make_crop_records(
            page,
            14,
            [anchor],
            [(0.0, 595.276)],
            margin_pt=4.0,
            footer_pt=70.0,
        )

        self.assertEqual(len(records), 1)
        self.assertAlmostEqual(records[0]["crop_rect_pt"]["y1"], 771.89, places=2)


if __name__ == "__main__":
    unittest.main()
