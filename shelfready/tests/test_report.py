import tempfile
import unittest
from pathlib import Path

from shelfready.report import criterion_percentages, html_report, json_report, write_html_report
from shelfready.scoring import score_catalog
from shelfready.tests.helpers import good_product


class HtmlReportTests(unittest.TestCase):
    def setUp(self):
        products = [good_product(id="A"), good_product(id="B", title="Daypack <script>x</script>", gtin="")]
        self.scores, self.catalog = score_catalog(products)

    def test_contains_score_and_products(self):
        page = html_report(self.scores, self.catalog, [])
        self.assertIn(f"{self.catalog}", page)
        self.assertIn("Score by criterion", page)
        self.assertIn("Distinctive attributes", page)
        self.assertIn(">A<", page)

    def test_escapes_html_in_product_data(self):
        page = html_report(self.scores, self.catalog, [])
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)

    def test_lists_skipped_rows(self):
        page = html_report(self.scores, self.catalog, ["Line 9: missing id"])
        self.assertIn("Rows skipped", page)
        self.assertIn("Line 9: missing id", page)

    def test_criterion_percentages(self):
        percentages = criterion_percentages(self.scores)
        self.assertEqual(set(percentages), {
            "Distinctive attributes", "Disambiguation", "Price / content coherence", "Structuring",
        })
        self.assertEqual(percentages["Distinctive attributes"], 100)
        self.assertLess(percentages["Disambiguation"], 100)

    def test_json_report_can_be_saved(self):
        import json
        data: dict = json_report(self.scores, self.catalog, ["Line 9: missing id"], "shop.csv", "Outdoor")
        self.assertEqual(data["product_count"], 2)
        self.assertEqual(data["skipped_rows"], ["Line 9: missing id"])
        text: str = json.dumps(data) # fails if something cannot be turned into JSON
        self.assertIn('"catalog_score"', text)

    def test_uses_plain_rule_names(self):
        # product B has no barcode: the page says it in plain words, with the fix
        page = html_report(self.scores, self.catalog, [])
        self.assertIn("Barcode missing or wrong", page)
        self.assertIn("Fix: Copy the barcode from the box", page)
        self.assertNotIn("<strong>gtin</strong>", page)

    def test_every_rule_has_a_name_and_a_fix(self):
        from shelfready.report import HOW_TO_FIX, RULE_NAMES
        from shelfready.rules import POINTS
        for rule in POINTS:
            self.assertIn(rule, RULE_NAMES)
            self.assertIn(rule, HOW_TO_FIX)

    def test_write_creates_folder_and_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_html_report(Path(tmp) / "reports" / "r.html", self.scores, self.catalog, [])
            self.assertTrue(path.exists())
            self.assertTrue(path.read_text(encoding="utf-8").startswith("<!DOCTYPE html>"))


if __name__ == "__main__":
    unittest.main()
