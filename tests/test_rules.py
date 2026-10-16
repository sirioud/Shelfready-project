import unittest

from shelfready import rules
from shelfready.models import Product, RuleResult
from tests.helpers import good_product


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
            description="Down sleeping bag for winter camping.",
            attributes="comfort_c: -2 | limit_c: -8 | extreme_c: -24 | weight_g: 1250",
        )
        self.assertTrue(rules.check_spec_agreement(bag).passed)
        # -10 °C is none of the three ratings: that is a real contradiction
        wrong: Product = good_product(
            category="sleeping_bag",
            title="Down bag -10 °C",
            description="Down sleeping bag for winter camping.",
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



class SpecAgreementInDescriptionTests(unittest.TestCase):
    def test_description_contradicts_attribute(self):
        # the title is fine, but the description says 25 l and the attribute 30
        product: Product = good_product(description="Hiking daypack with a rain cover. It holds 25 l and weighs 900 g.")
        result: RuleResult = rules.check_spec_agreement(product)
        self.assertFalse(result.passed)
        self.assertIn("description says 25 l", result.message)

    def test_description_agrees(self):
        self.assertTrue(rules.check_spec_agreement(good_product()).passed)


class ClearWordingTests(unittest.TestCase):
    def test_facts_not_claims_passes_on_good_product(self):
        self.assertTrue(rules.check_facts_not_claims(good_product()).passed)

    def test_marketing_words_without_numbers_fail(self):
        product: Product = good_product(description="Premium daypack, the ultimate pack for every adventure.")
        result: RuleResult = rules.check_facts_not_claims(product)
        self.assertFalse(result.passed)
        self.assertIn("premium", result.message)
        self.assertIn("ultimate", result.message)

    def test_marketing_words_backed_by_numbers_pass(self):
        # two claims, but the title and description give two numbers with units
        product: Product = good_product(description="Premium daypack, the ultimate pack: it holds 30 l and weighs 900 g.")
        self.assertTrue(rules.check_facts_not_claims(product).passed)

    def test_one_marketing_word_is_fine(self):
        product: Product = good_product(description="Daypack with the best rain cover we make.")
        self.assertTrue(rules.check_facts_not_claims(product).passed)

    def test_word_inside_another_word_is_not_a_claim(self):
        # "best" must not be found inside "bestseller"
        self.assertEqual(rules.marketing_words_in("Our bestseller"), [])

    def test_keyword_stuffing_passes_on_good_product(self):
        self.assertTrue(rules.check_keyword_stuffing(good_product()).passed)

    def test_repeated_word_in_title(self):
        product: Product = good_product(title="Backpack hiking backpack camping backpack 30 l")
        result: RuleResult = rules.check_keyword_stuffing(product)
        self.assertFalse(result.passed)
        self.assertIn("backpack", result.message)

    def test_short_words_can_repeat(self):
        # "of" twice is normal in a title
        product: Product = good_product(title="Socks pack of 2 for kids of 6 to 10")
        self.assertTrue(rules.check_keyword_stuffing(product).passed)

    def test_title_as_keyword_list(self):
        product: Product = good_product(title="Daypack, hiking, camping, travel")
        self.assertFalse(rules.check_keyword_stuffing(product).passed)

    def test_title_too_long(self):
        product: Product = good_product(title="Daypack " + "x" * 150)
        result: RuleResult = rules.check_keyword_stuffing(product)
        self.assertFalse(result.passed)
        self.assertIn("150 characters", result.message)

    def test_clear_opening_passes_on_good_product(self):
        # "Hiking daypack with a rain cover..." names the product
        self.assertTrue(rules.check_clear_opening(good_product()).passed)

    def test_opening_that_does_not_name_the_product(self):
        product: Product = good_product(description="Adventure awaits! A daypack for every trail.")
        self.assertFalse(rules.check_clear_opening(product).passed)

    def test_unknown_category_is_not_checked(self):
        product: Product = good_product(category="accessory", description="Adventure awaits!")
        self.assertTrue(rules.check_clear_opening(product).passed)

    def test_first_sentence(self):
        self.assertEqual(rules.first_sentence("Light daypack. Holds 30 l."), "Light daypack")
        self.assertEqual(rules.first_sentence("No full stop"), "No full stop")
        # the dot in "1.5" does not end the sentence
        self.assertEqual(rules.first_sentence("Holds 1.5 l of water. Light."), "Holds 1.5 l of water")


if __name__ == "__main__":
    unittest.main()
