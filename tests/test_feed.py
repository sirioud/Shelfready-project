import unittest

from shelfready.feed import with_unit


class FeedTests(unittest.TestCase):
    def test_with_unit_adds_the_unit(self):
        self.assertEqual(with_unit("volume_l", "30"), "30 l")
        self.assertEqual(with_unit("limit_c", "−8"), "−8 °C") # "−" is the typographic minus
        self.assertEqual(with_unit("material", "nylon"), "nylon") # no unit for a word


if __name__ == "__main__":
    unittest.main()
