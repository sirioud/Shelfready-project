import unittest

from shelfready.loader import LoaderError, load_products_from_text, parse_price

HEADER = "id,category,title,description,price,currency,availability,gtin,brand,image_url,attributes\n"


class LoaderTests(unittest.TestCase):
    def test_missing_column_raises(self):
        # the whole file is unusable: the loader stops with a LoaderError
        with self.assertRaises(LoaderError):
            load_products_from_text("id,title\nP1,Mug\n")

    def test_skips_row_with_bad_price(self):
        # only one row is bad: it is skipped, noted in errors, and the next row is still read
        products, errors = load_products_from_text(HEADER + "P1,mug,Mug,,abc,EUR,,,,,\n" + "P2,mug,Mug,,12,EUR,,,,,\n")
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].id, "P2")
        self.assertEqual(errors, ["Line 2: price is not a number"])

    def test_reads_semicolon_file_with_messy_header(self):
        # excel in switzerland and france separates the columns with ; and exports often write "ID" or " Title "
        products, errors = load_products_from_text("ID; Title ;Price\nP1;Mug;12,50\n")
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].title, "Mug")
        self.assertEqual(products[0].price, 12.5)

    def test_skips_duplicate_id(self):
        products, errors = load_products_from_text(HEADER + "P1,mug,Mug,,12,EUR,,,,,\n" + "P1,mug,Cup,,9,EUR,,,,,\n")
        self.assertEqual(len(products), 1)
        self.assertEqual(errors, ["Line 3: duplicate id P1 (already on line 2)"])

    def test_parse_price_refuses_nan_and_inf(self):
        # float accepts "nan" and "inf", but we don't want them in a price
        self.assertRaises(ValueError, parse_price, "nan")
        self.assertRaises(ValueError, parse_price, "inf")

    def test_parse_price_swiss_formats(self):
        self.assertEqual(parse_price("1'299.00"), 1299.0)
        self.assertEqual(parse_price("89.-"), 89.0)
        self.assertEqual(parse_price("1 299,50"), 1299.5)


if __name__ == "__main__":
    unittest.main()
