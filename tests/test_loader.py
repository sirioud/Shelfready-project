import tempfile
import unittest
from pathlib import Path

from shelfready.loader import LoaderError, load_products, load_products_from_text, parse_price

HEADER = "id,category,title,description,price,currency,availability,gtin,brand,image_url,attributes\n"


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write_csv(self, text):
        path = self.folder / "products.csv"
        path.write_text(text, encoding="utf-8")
        return path

    def test_reads_valid_row(self):
        path = self.write_csv(HEADER + "P1,mug,Mug,Nice mug,12.5,EUR,in_stock,,,,material: ceramic\n")
        products, errors = load_products(path)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].price, 12.5)
        self.assertEqual(products[0].attributes, "material: ceramic")
        self.assertEqual(errors, [])

    def test_skips_row_without_id(self):
        path = self.write_csv(HEADER + ",mug,Mug,,12,EUR,,,,,\n")
        products, errors = load_products(path)
        self.assertEqual(products, [])
        self.assertIn("missing id", errors[0])

    def test_skips_row_with_bad_price(self):
        path = self.write_csv(HEADER + "P1,mug,Mug,,abc,EUR,,,,,\n")
        products, errors = load_products(path)
        self.assertEqual(products, [])
        self.assertIn("price", errors[0])

    def test_skips_duplicate_id(self):
        path = self.write_csv(HEADER + "P1,mug,Mug,,12,EUR,,,,,\n" + "P1,mug,Other mug,,14,EUR,,,,,\n")
        products, errors = load_products(path)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].title, "Mug")
        self.assertIn("duplicate id P1 (already on line 2)", errors[0])

    def test_reads_excel_utf8_file(self):
        # Excel puts an invisible mark (BOM) before the first column name
        path = self.folder / "excel.csv"
        path.write_text(HEADER + "P1,mug,Mug,,12,EUR,,,,,\n", encoding="utf-8-sig")
        products, errors = load_products(path)
        self.assertEqual(len(products), 1)

    def test_reads_old_windows_file(self):
        path = self.folder / "windows.csv"
        path.write_text(HEADER + "P1,mug,Mug café,,12,EUR,,,,,\n", encoding="cp1252")
        products, errors = load_products(path)
        self.assertEqual(products[0].title, "Mug café")

    def test_folder_raises(self):
        with self.assertRaises(LoaderError):
            load_products(self.folder)

    def test_line_numbers_with_multiline_description(self):
        # the description of P1 goes over two lines, so the next row starts on line 4
        path = self.write_csv(HEADER + 'P1,mug,Mug,"First line\nsecond line",12,EUR,,,,,\n' + ",mug,No id,,12,EUR,,,,,\n")
        products, errors = load_products(path)
        self.assertEqual(products[0].description, "First line\nsecond line")
        self.assertEqual(errors, ["Line 4: missing id"])

    def test_load_from_text(self):
        # the web page gives text, not a path
        products, errors = load_products_from_text(HEADER + "P1,mug,Mug,,12,EUR,,,,,\n")
        self.assertEqual(products[0].id, "P1")
        self.assertEqual(errors, [])

    def test_missing_column_raises(self):
        path = self.write_csv("id,title\nP1,Mug\n")
        with self.assertRaises(LoaderError):
            load_products(path)

    def test_missing_file_raises(self):
        with self.assertRaises(LoaderError):
            load_products(self.folder / "nothing.csv")

    def test_reads_semicolon_csv(self):
        products, errors = load_products_from_text(HEADER.replace(",", ";") + "P1;mug;Mug;;12;EUR;;;;;\n")
        self.assertEqual(products[0].id, "P1")
        self.assertEqual(errors, [])
    
    def test_header_ignores_capitals_and_spaces(self):
        products, errors = load_products_from_text("ID , Category , Title , Description , Price , Currency , Availability , GTIN , Brand , Image URL , Attributes\n" + "P1,mug,Mug,,12,EUR,,,,,\n")
        self.assertEqual(products[0].id, "P1")
        self.assertEqual(errors, [])    

    def test_parse_price_accepts_comma(self):
        self.assertEqual(parse_price("12,50"), 12.5)
        self.assertIsNone(parse_price(""))

    def test_parse_price_refuses_nan_and_inf(self):
        #float accepts "nan" and "inf", but we don't want them in a price
        self.assertRaises(ValueError, parse_price, "nan")
        self.assertRaises(ValueError, parse_price, "inf")

    def test_parse_price_swiss_formats(self):
        self.assertEqual(parse_price("1'299.00"), 1299.0)
        self.assertEqual(parse_price("89.-"), 89.0)
        self.assertEqual(parse_price("1 299,50"), 1299.5)


if __name__ == "__main__":
    unittest.main()
