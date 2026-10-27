import unittest

from shelfready.report import html_report
from shelfready.scoring import score_catalog
from tests.helpers import good_product


class HtmlReportTests(unittest.TestCase):
    def test_escapes_html_in_product_data(self):
        # a title from the shop's file must be shown as text, never run as code in the browser
        scores, catalog = score_catalog([good_product(title="Daypack <script>x</script>")])
        page = html_report(scores, catalog, [])
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)


if __name__ == "__main__":
    unittest.main()
