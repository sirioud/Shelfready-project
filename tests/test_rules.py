import unittest

from shelfready import rules
from tests.helpers import good_product


class GtinTests(unittest.TestCase):
    def test_valid_codes(self):
        for code in ["4006381333931", "5901234123457", "96385074"]:
            self.assertTrue(rules.is_valid_gtin(code), code)

    def test_wrong_check_digit(self):
        self.assertFalse(rules.is_valid_gtin("4006381333932"))


class RuleTests(unittest.TestCase):
    def test_compatibility_in_capitals_is_still_vague(self):
        # "ALL" is two or more capitals, like the brand "MSR", but it names no model
        product = good_product(description="Hiking daypack. Compatible with ALL hydration bladders.")
        self.assertFalse(rules.check_compatibility(product).passed)

    def test_2_in_1_is_not_inches(self):
        # "2 in 1" must not be read as 2 inches and compared with the laptop size
        product = good_product(title="2 in 1 daypack 30 l", attributes="volume_l: 30 | weight_g: 900 | material: nylon | laptop_in: 15")
        self.assertTrue(rules.check_spec_agreement(product).passed)

    def test_currency_in_lower_case_is_accepted(self):
        self.assertTrue(rules.check_feed_standard(good_product(currency="eur")).passed)

    def test_feed_standard_needs_an_image(self):
        # google merchant center refuses a product without an image link
        self.assertFalse(rules.check_feed_standard(good_product(image_url="")).passed)

    def test_sleeping_bag_temperatures_go_down(self):
        # EN ISO 23537: comfort > limit > extreme. here comfort (-10) is colder than limit (-5)
        product = good_product(category="sleeping_bag", attributes="comfort_c: -10 | limit_c: -5 | extreme_c: -20 | weight_g: 1100")
        self.assertFalse(rules.check_plausible_values(product).passed)


class RegistryTests(unittest.TestCase):
    def test_points_add_up_to_100(self):
        self.assertEqual(sum(rules.POINTS.values()), 100)


if __name__ == "__main__":
    unittest.main()
