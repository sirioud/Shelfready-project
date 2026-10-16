import unittest

from shelfready.scoring import count_ready, count_unanswered, most_common_problems, score_catalog, score_product
from tests.helpers import good_product


class ScoringTests(unittest.TestCase):
    def test_perfect_product_scores_100(self):
        result = score_product(good_product())
        self.assertEqual(result.score, 100)
        self.assertTrue(result.is_ready)
        self.assertEqual(result.failed, [])

    def test_broken_product_loses_points(self):
        result = score_product(good_product(gtin="", title="Trail daypack 25 l"))
        self.assertLess(result.score, 100)
        self.assertEqual({r.rule for r in result.failed}, {"gtin", "spec_agreement"})

    def test_catalog_average(self):
        products = [good_product(id="A"), good_product(id="B", gtin="")]
        scores, catalog = score_catalog(products)
        self.assertEqual(len(scores), 2)
        self.assertEqual(catalog, (100 + scores[1].score) / 2)

    def test_blocked_product_is_not_ready(self):
        # brand "N/A" fails feed_standard: 90 points, but the feed would reject it
        result = score_product(good_product(brand="N/A"))
        self.assertEqual(result.score, 90)
        self.assertTrue(result.blocked)
        self.assertFalse(result.is_ready)

    def test_to_dict(self):
        result = score_product(good_product(id="A", brand="N/A"))
        data: dict = result.to_dict()
        self.assertEqual(data["id"], "A")
        self.assertEqual(data["score"], 90)
        self.assertFalse(data["ready"])
        self.assertTrue(data["blocked"])
        self.assertEqual(data["failed"][0]["rule"], "feed_standard")
        self.assertEqual(data["cannot_be_matched"], [])

    def test_count_ready_and_unanswered(self):
        products = [
            good_product(id="A"),
            good_product(id="B", brand="N/A"), # blocked, so not ready
            good_product(id="C", attributes="material: nylon"), # no volume_l, no weight_g: 2 questions unknown
        ]
        scores, _ = score_catalog(products)
        self.assertEqual(count_ready(scores), 1)
        self.assertEqual(count_unanswered(scores), 2)

    def test_empty_catalog(self):
        self.assertEqual(score_catalog([]), ([], 0.0))

    def test_most_common_problems(self):
        products = [good_product(id="A", gtin=""), good_product(id="B", gtin="", attributes="color: red")]
        scores, _ = score_catalog(products)
        self.assertEqual(most_common_problems(scores)[0], ("gtin", 2))


if __name__ == "__main__":
    unittest.main()
