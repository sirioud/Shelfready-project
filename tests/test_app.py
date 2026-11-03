import os
import unittest
from pathlib import Path

import shelfready.ai_search

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
    def setUp(self):
        # no Gemini key during the tests: no variable, and a creds file that does not exist
        self.saved_key = os.environ.pop("GEMINI_API_KEY", None)
        self.saved_creds = shelfready.ai_search.CREDS_FILE
        shelfready.ai_search.CREDS_FILE = Path("no_such_folder") / "gemini_creds.json"

    def tearDown(self):
        shelfready.ai_search.CREDS_FILE = self.saved_creds
        if self.saved_key is not None:
            os.environ["GEMINI_API_KEY"] = self.saved_key

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

    def test_ai_tab_replays_recorded_run_without_key(self):
        app = AppTest.from_file(str(APP_FILE)).run(timeout=APP_TIMEOUT)
        app.checkbox[0].check().run(timeout=APP_TIMEOUT)
        self.assertEqual(len(app.exception), 0)
        live_buttons = []
        for button in app.button:
            if button.label == "Run with live AI":
                live_buttons.append(button)
        self.assertEqual(len(live_buttons), 1)
        self.assertTrue(live_buttons[0].disabled) # no key: the live test cannot run
        captions: list[str] = []
        for caption in app.caption:
            captions.append(caption.value)
        self.assertTrue(any("Recorded run" in text for text in captions))


if __name__ == "__main__":
    unittest.main()
