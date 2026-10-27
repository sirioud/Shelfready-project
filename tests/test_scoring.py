import unittest

from shelfready.scoring import score_product
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

    def test_blocked_product_is_not_ready(self):
        # brand "N/A" fails feed_standard: 90 points, but the feed would reject it
        result = score_product(good_product(brand="N/A"))
        self.assertEqual(result.score, 90)
        self.assertTrue(result.blocked)
        self.assertFalse(result.is_ready)


if __name__ == "__main__":
    unittest.main()
