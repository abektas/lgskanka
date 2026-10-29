#!/usr/bin/env python3
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "source-ingestion"))

from nuli_qbank_pdf_extractor import (  # noqa: E402
    DEFAULT_MARGIN_PT,
    QuestionAnchor,
    make_crop_records,
)


class CropMarginTest(unittest.TestCase):
    def test_default_margin_leaves_room_above_superscripts(self):
        self.assertEqual(DEFAULT_MARGIN_PT, 18.0)

    def test_explicit_margin_applies_above_question_anchor(self):
        page = SimpleNamespace(height=841.89)
        anchor = QuestionAnchor(13, 28.3, 44.7, 36.7, 55.0, 0, 0.85, "13.")
        records = make_crop_records(
            page, 14, [anchor], [(0.0, 595.276)], margin_pt=8.0, footer_pt=70.0
        )
        self.assertAlmostEqual(records[0]["crop_rect_pt"]["y0"], 36.7, places=2)

    def test_margin_is_applied_to_left_and_right_edges(self):
        page = SimpleNamespace(height=841.89)
        anchor = QuestionAnchor(13, 28.3, 44.7, 36.7, 55.0, 0, 0.85, "13.")
        records = make_crop_records(
            page, 14, [anchor], [(0.0, 595.276)], margin_pt=18.0, footer_pt=70.0
        )
        rect = records[0]["crop_rect_pt"]
        self.assertAlmostEqual(rect["x0"], 18.0, places=2)
        self.assertAlmostEqual(rect["x1"], 577.276, places=2)


if __name__ == "__main__":
    unittest.main()
