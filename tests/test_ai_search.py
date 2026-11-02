import os
import tempfile
import unittest
from pathlib import Path

from shelfready.ai_search import (
    BENEFIT_UNCLEAR,
    GUESSED,
    SKIPPED,
    AISearchError,
    load_api_key,
    parse_answer,
    rows_for_need,
    run_search,
    verdict,
)
from shelfready.questions import UNKNOWN, YES
from shelfready.sector import NEED_QUESTIONS
from tests.helpers import good_product


class VerdictTests(unittest.TestCase):
    def test_benefit_unclear(self):
        # the specs prove the product fits, but the AI did not recommend it
        self.assertEqual(verdict(YES, False), BENEFIT_UNCLEAR)

    def test_guessed_without_attribute(self):
        # the AI recommended it although the spec it needs is missing
        self.assertEqual(verdict(UNKNOWN, True), GUESSED)


class ParseTests(unittest.TestCase):
    def test_bad_answer_raises(self):
        with self.assertRaises(AISearchError):
            parse_answer("not json", ["P1"])

    def test_fenced_answer_unknown_and_missing_ids(self):
        # Gemini sometimes wraps its JSON in ```json ... ```, and can name an id that is not in the list
        text = '```json\n[{"id": "P1", "recommended": true, "reason": "Warm enough."}, {"id": "X9", "recommended": true, "reason": "?"}]\n```'
        picks = parse_answer(text, ["P1", "P2"])
        self.assertEqual(picks["P1"], (True, "Warm enough."))
        self.assertEqual(picks["P2"], (False, "No answer from the AI."))
        self.assertNotIn("X9", picks)


class SearchTests(unittest.TestCase):
    # none of these tests calls Gemini: the answers are fixed texts
    def test_rows_for_need(self):
        fits = good_product(id="T1") # volume_l 30 -> fits the weekend need (30 l or more)
        small = good_product(id="T2", attributes="volume_l: 20 | weight_g: 900 | material: nylon")
        answer = '[{"id": "T1", "recommended": false, "reason": "Not sure."}, {"id": "T2", "recommended": false, "reason": "Too small."}]'
        rows = rows_for_need(NEED_QUESTIONS["backpack"][0], [fits, small], answer)
        self.assertEqual([row["verdict"] for row in rows], [BENEFIT_UNCLEAR, SKIPPED])

    def test_no_need_for_category_makes_no_call(self):
        # no key: a call to Gemini would fail, so [] proves no call was made
        self.assertEqual(run_search([good_product(category="socks")], ""), [])

    def test_recorded_run_without_answer_raises(self):
        with self.assertRaises(AISearchError):
            run_search([good_product()], "", recorded={"answers": {}})

    def test_load_api_key_from_file(self):
        saved = os.environ.pop("GEMINI_API_KEY", None) # the variable would win over the file
        try:
            with tempfile.TemporaryDirectory() as folder:
                good_file = Path(folder) / "good.json"
                good_file.write_text('{"api_key": "abc"}')
                bad_file = Path(folder) / "bad.json"
                bad_file.write_text("not json")
                self.assertEqual(load_api_key(good_file), "abc")
                self.assertEqual(load_api_key(bad_file), "")
        finally:
            if saved is not None:
                os.environ["GEMINI_API_KEY"] = saved


if __name__ == "__main__":
    unittest.main()
