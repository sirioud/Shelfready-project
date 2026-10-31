import unittest

from shelfready.report import BASIS_OF_RULE, CRITERIA, HOW_TO_FIX, RULE_NAMES, pdf_report
from shelfready.rules import CRITERION_OF_RULE, POINTS
from shelfready.scoring import score_catalog
from tests.helpers import good_product


class PdfReportTests(unittest.TestCase):
    def test_pdf_with_unusual_characters(self):
        # the pdf fonts only know latin-1: a minus sign, a euro sign or an emoji must not crash the download
        scores, catalog = score_catalog([good_product(title="Daypack −8 °C 49 € 🎒")])
        report = pdf_report(scores, catalog, ["Line 3: price is not a number"])
        self.assertTrue(report.startswith(b"%PDF"))

    def test_every_rule_has_its_texts_and_a_known_criterion(self):
        # a new rule in RULE_REGISTRY also needs these texts, otherwise the page crashes with a KeyError
        for rule in POINTS:
            self.assertIn(rule, RULE_NAMES)
            self.assertIn(rule, HOW_TO_FIX)
            self.assertIn(rule, BASIS_OF_RULE)
            self.assertIn(CRITERION_OF_RULE[rule], CRITERIA)


if __name__ == "__main__":
    unittest.main()
