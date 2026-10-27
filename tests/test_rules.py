import unittest

from shelfready import rules


class GtinTests(unittest.TestCase):
    def test_valid_codes(self):
        for code in ["4006381333931", "5901234123457", "96385074"]:
            self.assertTrue(rules.is_valid_gtin(code), code)

    def test_wrong_check_digit(self):
        self.assertFalse(rules.is_valid_gtin("4006381333932"))


class RegistryTests(unittest.TestCase):
    def test_points_add_up_to_100(self):
        self.assertEqual(sum(rules.POINTS.values()), 100)


if __name__ == "__main__":
    unittest.main()
