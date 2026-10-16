import unittest

from shelfready.attributes import bare_numbers, parse_attributes, plain_name, specs_in_text, to_number
from shelfready.sector import Attribute_labels, Expected_attributes, Shopper_questions


class AttributeTests(unittest.TestCase):
    def test_parse_pairs(self):
        parsed = parse_attributes("volume_l: 30 | material: nylon")
        self.assertEqual(parsed, {"volume_l": "30", "material": "nylon"})

    def test_ignores_broken_chunks(self):
        self.assertEqual(parse_attributes("volume_l 30 | : nylon | "), {})

    def test_specs_in_text(self):
        self.assertEqual(specs_in_text("holds 750 ml and weighs 900 g"), [("750", "ml"), ("900", "g")])

    def test_outdoor_units(self):
        self.assertEqual(specs_in_text("400 lm for 20 h"), [("400", "lm"), ("20", "h")])
        self.assertEqual(specs_in_text("comfort at 0 °C"), [("0", "°c")])
        self.assertEqual(bare_numbers("comfort at 0 °C"), [])

    def test_bare_numbers(self):
        self.assertEqual(bare_numbers("fits 15 in laptops"), [])
        self.assertEqual(bare_numbers("for runners under 75 kilos"), ["75"])
        self.assertEqual(bare_numbers("pack of 4 brushes"), [])

    def test_negative_temperatures(self):
        # a sleeping bag rated -8 °C must keep its minus sign
        self.assertEqual(specs_in_text("limit -8 °C, extreme -24 °C"), [("-8", "°c"), ("-24", "°c")])
        self.assertEqual(bare_numbers("comfort -2 °C"), [])
        # a hyphen inside a word is not a minus sign
        self.assertEqual(specs_in_text("2-person tent of 1800 g"), [("1800", "g")])

    def test_number_before_full_stop(self):
        self.assertEqual(bare_numbers("for children aged 6 to 10."), ["6", "10"])
        self.assertEqual(bare_numbers("costs 12.5 today"), ["12.5"])

    def test_minutes_are_a_unit(self):
        self.assertEqual(bare_numbers("boils 1 l of water in 3 minutes"), [])

    def test_to_number(self):
        self.assertEqual(to_number("1100"), 1100.0)
        self.assertEqual(to_number("-2"), -2.0)
        self.assertEqual(to_number("1,5"), 1.5)
        self.assertEqual(to_number("30 l"), 30.0)
        self.assertIsNone(to_number("light"))
        self.assertEqual(to_number("30l"), 30.0) # unit stuck to the number
        self.assertEqual(to_number("−8"), -8.0) # typographic minus sign


    def test_plain_name(self):
        self.assertEqual(plain_name("limit_c"), "limit temperature in °C (limit_c)")
        self.assertEqual(plain_name("unknown_key"), "unknown_key") # no label: the key is shown as it is

    def test_every_needed_attribute_has_a_label(self):
        # the reports must never show a bare key for an attribute the tool asks for
        for category in Expected_attributes:
            for key in Expected_attributes[category]:
                self.assertIn(key, Attribute_labels)
        for category in Shopper_questions:
            for question in Shopper_questions[category]:
                self.assertIn(question[1], Attribute_labels)


if __name__ == "__main__":
    unittest.main()
