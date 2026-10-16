import unittest

from shelfready.feed import highlights_of, questions_and_answers, short_label, supplemental_feed, with_unit
from shelfready.models import Product
from shelfready.tests.helpers import good_product


class FeedTests(unittest.TestCase):
    def test_short_label(self):
        self.assertEqual(short_label("volume_l"), "Volume")
        self.assertEqual(short_label("size_system"), "Size system")
        self.assertEqual(short_label("unknown_key"), "Unknown_key")

    def test_with_unit(self):
        self.assertEqual(with_unit("volume_l", "30"), "30 l")
        self.assertEqual(with_unit("limit_c", "-8"), "-8 °C")
        self.assertEqual(with_unit("power_w", "3000"), "3000 W")
        self.assertEqual(with_unit("volume_l", "30 l"), "30 l") # already has its unit
        self.assertEqual(with_unit("material", "nylon"), "nylon")

    def test_highlights_from_attributes(self):
        self.assertEqual(highlights_of(good_product()), ["Volume: 30 l", "Weight: 900 g", "Material: nylon"])

    def test_fewer_than_two_highlights_are_not_sent(self):
        # google merchant center needs at least 2
        self.assertEqual(highlights_of(good_product(attributes="material: nylon")), [])

    def test_questions_answered_yes_and_no(self):
        bag: Product = good_product(category="sleeping_bag", attributes="limit_c: -8 | weight_g: 1800")
        pairs: list[tuple[str, str]] = questions_and_answers(bag)
        self.assertIn(("Is it warm enough for a night at -5 °C?", "Yes, limit temperature is -8 °C."), pairs)
        self.assertIn(("Does it weigh less than 1.5 kg?", "No, weight is 1800 g."), pairs)

    def test_missing_attribute_gives_no_answer(self):
        # no limit temperature: we do not guess an answer
        bag: Product = good_product(category="sleeping_bag", attributes="comfort_c: 0 | weight_g: 1100")
        questions: list[str] = []
        for question, reply in questions_and_answers(bag):
            questions.append(question)
        self.assertNotIn("Is it warm enough for a night at -5 °C?", questions)

    def test_feed_is_tab_separated_with_quoted_values(self):
        lines: list[str] = supplemental_feed([good_product(id="A")]).splitlines()
        self.assertEqual(lines[0], "id\tproduct_highlight\tquestion_and_answer")
        columns: list[str] = lines[1].split("\t")
        self.assertEqual(columns[0], "A")
        self.assertEqual(columns[1], '"Volume: 30 l", "Weight: 900 g", "Material: nylon"')
        self.assertIn('"Does it weigh less than 1 kg?":"Yes, weight is 900 g."', columns[2])

    def test_contradicted_listing_is_left_out(self):
        # the title says 25 l but the attribute 30: fix it before sending it to google
        wrong: Product = good_product(id="B", title="Trail daypack 25 l")
        lines: list[str] = supplemental_feed([good_product(id="A"), wrong]).splitlines()
        self.assertEqual(len(lines), 2) # header + A only

    def test_quotes_and_tabs_cannot_break_the_file(self):
        product: Product = good_product(attributes='material: "nylon"\tblend | weight_g: 900')
        line: str = supplemental_feed([product]).splitlines()[1]
        self.assertEqual(line.count("\t"), 2)
        self.assertIn("Material: 'nylon' blend", line)


if __name__ == "__main__":
    unittest.main()
