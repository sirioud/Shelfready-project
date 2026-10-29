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


class RegistryTests(unittest.TestCase):
    def test_points_add_up_to_100(self):
        self.assertEqual(sum(rules.POINTS.values()), 100)


if __name__ == "__main__":
    unittest.main()
