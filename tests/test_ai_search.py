import unittest

from shelfready.ai_search import BENEFIT_UNCLEAR, GUESSED, AISearchError, parse_answer, verdict
from shelfready.questions import UNKNOWN, YES


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


if __name__ == "__main__":
    unittest.main()
