import unittest
from pathlib import Path

# the web page needs streamlit, which is only in the nomades_nppd_312 environment
try:
    from streamlit.testing.v1 import AppTest
    HAS_STREAMLIT: bool = True
except ImportError:
    HAS_STREAMLIT = False

APP_FILE: Path = Path(__file__).parent.parent / "shelfready_app.py"
# seconds streamlit may take to run the page. its default of 3 is too short on a cold start or under coverage
APP_TIMEOUT: int = 15


@unittest.skipUnless(HAS_STREAMLIT, "streamlit is not installed in this environment")
class AppTests(unittest.TestCase):
    def test_start_page_asks_for_a_file(self):
        app = AppTest.from_file(str(APP_FILE)).run(timeout=APP_TIMEOUT)
        self.assertEqual(len(app.exception), 0)
        self.assertIn("Upload a CSV file", app.info[0].value)

    def test_sample_shop(self):
        app = AppTest.from_file(str(APP_FILE)).run(timeout=APP_TIMEOUT)
        app.checkbox[0].check().run(timeout=APP_TIMEOUT)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[0].value, "85.3 / 100")
        self.assertEqual(app.metric[1].value, "5 of 10")
        # the sample scores 85.3, which grades "good", so the verdict is a green success box
        self.assertIn("5 of 10 listings are ready", app.success[0].value)
        # the two skipped rows of the sample file are shown as warnings
        warnings: list[str] = []
        for box in app.warning:
            warnings.append(box.value)
        self.assertIn("Line 9: missing id", warnings)
        self.assertIn("Line 12: price is not a number", warnings)
        # the listings tab opens on the worst listing
        self.assertIn("P005", app.expander[0].label)


if __name__ == "__main__":
    unittest.main()
