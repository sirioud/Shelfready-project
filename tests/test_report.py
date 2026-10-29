import unittest

from shelfready.report import BASIS_OF_RULE, CRITERIA, HOW_TO_FIX, RULE_NAMES, html_report
from shelfready.rules import CRITERION_OF_RULE, POINTS
from shelfready.scoring import score_catalog
from tests.helpers import good_product


class HtmlReportTests(unittest.TestCase):
    def test_escapes_html_in_product_data(self):
        # a title from the shop's file must be shown as text, never run as code in the browser
        scores, catalog = score_catalog([good_product(title="Daypack <script>x</script>")])
        page = html_report(scores, catalog, [])
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)

    def test_every_rule_has_its_texts_and_a_known_criterion(self):
        # a new rule in RULE_REGISTRY also needs these texts, otherwise the page crashes with a KeyError
        for rule in POINTS:
            self.assertIn(rule, RULE_NAMES)
            self.assertIn(rule, HOW_TO_FIX)
            self.assertIn(rule, BASIS_OF_RULE)
            self.assertIn(CRITERION_OF_RULE[rule], CRITERIA)


if __name__ == "__main__":
    unittest.main()
