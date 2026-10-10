import unittest

from shelfready import rules
from shelfready.models import Product, RuleResult
from shelfready.tests.helpers import good_product


class GtinTests(unittest.TestCase):
    def test_valid_codes(self):
        for code in ["4006381333931", "5901234123457", "96385074"]:
            self.assertTrue(rules.is_valid_gtin(code), code)

    def test_wrong_check_digit(self):
        self.assertFalse(rules.is_valid_gtin("4006381333932"))

    def test_bad_format(self):
        for code in ["", "abc", "12345"]:
            self.assertFalse(rules.is_valid_gtin(code), code)


class RuleTests(unittest.TestCase):
    def test_good_product_passes_every_rule(self):
        product = good_product()
        for rule in rules.All_rules:
            self.assertTrue(rule(product).passed, rule.__name__)

    def test_each_rule_can_fail(self):
        cases = [
            (rules.check_expected_attributes, {"attributes": "material: nylon | color: red | size: M"}),
            (rules.check_attribute_count, {"attributes": "volume_l: 30 | weight_g: 900"}),
            (rules.check_units, {"description": "Fits laptops up to 15 and weighs little."}),
            (rules.check_compatibility, {"description": "Compatible with most laptops on the market."}),
            (rules.check_quantity, {"title": "Daypack set of 2"}),
            (rules.check_gtin, {"gtin": "4006381333932"}),
            (rules.check_feed_standard, {"availability": "available"}),
            (rules.check_price_coherence, {"price": 249.0, "description": "A bag."}),
            (rules.check_spec_agreement, {"title": "Trail daypack 25 l"}),
            (rules.check_plausible_values, {"attributes": "volume_l: 30 | weight_g: 0.9 | material: nylon"}),
            (rules.check_structured_share, {"attributes": "color: red | brand_line: trail | season: summer"}),
        ]
        for rule, changes in cases:
            with self.subTest(rule=rule.__name__, changes=changes):
                result = rule(good_product(**changes))
                self.assertFalse(result.passed)
                self.assertEqual(result.points, 0)
                self.assertNotEqual(result.message, "")

    def test_sleeping_bag_needs_all_three_iso_ratings(self):
        bag = good_product(category="sleeping_bag", attributes="comfort_c: 0 | weight_g: 1100 | material: down")
        result = rules.check_expected_attributes(bag)
        self.assertFalse(result.passed)
        self.assertIn("limit_c", result.message)
        self.assertIn("extreme_c", result.message)
        full = good_product(
            category="sleeping_bag",
            attributes="comfort_c: 0 | limit_c: -6 | extreme_c: -22 | weight_g: 1100",
        )
        self.assertTrue(rules.check_expected_attributes(full).passed)

    def test_footwear_needs_feed_attributes(self):
        shoes = good_product(category="shoes", attributes="size: 42 | color: black")
        self.assertFalse(rules.check_expected_attributes(shoes).passed)

    def test_feed_standard_values(self):
        self.assertTrue(rules.check_feed_standard(good_product(availability="in stock")).passed)
        self.assertFalse(rules.check_feed_standard(good_product(brand="Generic")).passed)
        self.assertFalse(rules.check_feed_standard(good_product(currency="euro")).passed)

    def test_feed_standard_needs_title_and_price(self):
        self.assertFalse(rules.check_feed_standard(good_product(title="")).passed)
        self.assertFalse(rules.check_feed_standard(good_product(price=None)).passed)

    def test_compatibility_needs_with(self):
        # "helmet-compatible hood" describes the hood, it is not a compatibility claim
        jacket: Product = good_product(description="Rain jacket with a helmet-compatible hood.")
        self.assertTrue(rules.check_compatibility(jacket).passed)
        # a brand written in capitals counts as precise
        stove: Product = good_product(description="Stove compatible with MSR IsoPro cartridges.")
        self.assertTrue(rules.check_compatibility(stove).passed)

    def test_plausible_ranges(self):
        # 1.2 is a weight in kg written in the weight_g field
        bag: Product = good_product(attributes="volume_l: 30 | weight_g: 1.2 | material: nylon")
        result: RuleResult = rules.check_plausible_values(bag)
        self.assertFalse(result.passed)
        self.assertIn("weight_g", result.message)

    def test_plausible_needs_a_number(self):
        bag: Product = good_product(attributes="volume_l: 30 | weight_g: light | material: nylon")
        self.assertFalse(rules.check_plausible_values(bag).passed)

    def test_sleeping_bag_temperatures_go_down(self):
        right: Product = good_product(category="sleeping_bag", attributes="comfort_c: -2 | limit_c: -8 | extreme_c: -24 | weight_g: 1250")
        self.assertTrue(rules.check_plausible_values(right).passed)
        # limit and comfort swapped
        wrong: Product = good_product(category="sleeping_bag", attributes="comfort_c: -8 | limit_c: -2 | extreme_c: -24 | weight_g: 1250")
        result: RuleResult = rules.check_plausible_values(wrong)
        self.assertFalse(result.passed)
        self.assertIn("limit_c", result.message)

    def test_negative_temperatures_count_as_structured(self):
        bag: Product = good_product(
            category="sleeping_bag",
            description="Winter bag. Comfort -2 °C, limit -8 °C, extreme -24 °C.",
            attributes="comfort_c: -2 | limit_c: -8 | extreme_c: -24 | weight_g: 1250",
        )
        self.assertTrue(rules.check_structured_share(bag).passed)

    def test_sleeping_bag_title_matches_one_of_three_temperatures(self):
        # the title gives the limit temperature, it must not be compared with comfort and extreme
        bag: Product = good_product(
            category="sleeping_bag",
            title="Down bag -8 °C",
            attributes="comfort_c: -2 | limit_c: -8 | extreme_c: -24 | weight_g: 1250",
        )
        self.assertTrue(rules.check_spec_agreement(bag).passed)
        # -10 °C is none of the three ratings: that is a real contradiction
        wrong: Product = good_product(
            category="sleeping_bag",
            title="Down bag -10 °C",
            attributes="comfort_c: -2 | limit_c: -8 | extreme_c: -24 | weight_g: 1250",
        )
        self.assertFalse(rules.check_spec_agreement(wrong).passed)

    def test_same_number_written_differently(self):
        # "30.0" and "30l" are the same value as "30 l" in the title and description
        for volume in ["30.0", "30l", "30 l"]:
            product: Product = good_product(attributes=f"volume_l: {volume} | weight_g: 900 | material: nylon")
            with self.subTest(volume=volume):
                self.assertTrue(rules.check_spec_agreement(product).passed)
                self.assertTrue(rules.check_structured_share(product).passed)

    def test_points_add_up_to_100(self):
        self.assertEqual(sum(rules.Points.values()), 100)

    def test_every_rule_has_points(self):
        names = {r.__name__.replace("check_", "") for r in rules.All_rules}
        self.assertEqual(names, set(rules.Points))


if __name__ == "__main__":
    unittest.main()
