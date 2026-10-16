import unittest

from shelfready.questions import No, Unknown, Yes, answer_question, question_summary, unanswered_questions
from tests.helpers import good_product

# question = (text, attribute, test, wanted value), as in sector.py
Cold_night: tuple = ("A sleeping bag for a night at -5 °C", "limit_c", "at_most", -5)


class QuestionTests(unittest.TestCase):
    def test_yes_no_unknown(self):
        warm_bag = good_product(category="sleeping_bag", attributes="comfort_c: -2 | limit_c: -8 | extreme_c: -24")
        summer_bag = good_product(category="sleeping_bag", attributes="comfort_c: 10 | limit_c: 5 | extreme_c: -5")
        comfort_only = good_product(category="sleeping_bag", attributes="comfort_c: 0 | weight_g: 1100")
        self.assertEqual(answer_question(warm_bag, Cold_night), Yes)
        self.assertEqual(answer_question(summer_bag, Cold_night), No)
        self.assertEqual(answer_question(comfort_only, Cold_night), Unknown)

    def test_equals_ignores_case(self):
        shoes = good_product(category="shoes", attributes="size: 42 | gender: Unisex")
        self.assertEqual(answer_question(shoes, ("Unisex shoes", "gender", "equals", "unisex")), Yes)

    def test_unanswered_questions(self):
        comfort_only = good_product(category="sleeping_bag", attributes="comfort_c: 0 | weight_g: 1100")
        missing: list[str] = unanswered_questions(comfort_only)
        self.assertEqual(missing, ["A sleeping bag for a night at -5 °C: needs the limit temperature in °C (limit_c)"])
        # a category without questions has nothing to answer
        self.assertEqual(unanswered_questions(good_product(category="tent")), [])

    def test_summary_only_lists_categories_in_the_catalog(self):
        products = [good_product(id="A"), good_product(id="B", attributes="material: nylon")]
        summary: list[dict] = question_summary(products)
        self.assertEqual(len(summary), 2) # the two backpack questions
        self.assertEqual(summary[0]["matches"], ["A"])
        self.assertEqual(summary[0]["unknown"], ["B"])


if __name__ == "__main__":
    unittest.main()
