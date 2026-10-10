import unittest
from pathlib import Path

# the web page needs streamlit, which is only in the nomades_nppd_312 environment
try:
    from streamlit.testing.v1 import AppTest
    Has_streamlit: bool = True
except ImportError:
    Has_streamlit = False

App_file: Path = Path(__file__).parent.parent.parent / "shelfready_app.py"


@unittest.skipUnless(Has_streamlit, "streamlit is not installed in this environment")
class AppTests(unittest.TestCase):
    def test_start_page_asks_for_a_file(self):
        app = AppTest.from_file(str(App_file)).run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("Upload a CSV file", app.info[0].value)

    def test_sample_shop(self):
        app = AppTest.from_file(str(App_file)).run()
        app.checkbox[0].check().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[0].value, "85.5 / 100")
        self.assertEqual(app.metric[1].value, "4 of 10")
        # the verdict at the top, then the two skipped rows of the sample file
        warnings: list[str] = []
        for box in app.warning:
            warnings.append(box.value)
        self.assertIn("4 of 10 listings are ready", warnings[0])
        self.assertIn("Line 9: missing id", warnings)
        self.assertIn("Line 12: price is not a number", warnings)
        # the listings tab opens on the worst listing
        self.assertIn("P003", app.expander[0].label)


if __name__ == "__main__":
    unittest.main()
