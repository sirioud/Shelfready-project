# The loader reads the product csv file and turns each row into a Product object.
# It stops if the whole file is unusable (unreadable encoding, required columns missing).
# If only one row is bad (no id, price is not a number) it skips that row, notes it and continues.

import csv
import io
import math
from .models import Product

# columns the file must have, otherwise we cannot do anything
REQUIRED_COLUMNS: set[str] = {"id", "title", "price"}


class LoaderError(Exception):
    # raised when the whole file cannot be read
    pass


def parse_price(raw: str | None) -> float | None:
    # turns the price cell into a float, or None when the cell is empty
    # accepts swiss and french formats found in shop exports
    text: str = ""
    if raw is not None:
        text = raw.strip()

    if text == "":
        return None

    text = text.replace("'", "") # swiss thousands separator: 1'299.00
    text = text.replace("’", "") # same separator typed as a curly apostrophe
    text = text.replace(" ", "") # non-breaking space, common in exports
    text = text.replace(" ", "") # plain space as separator

    if text.endswith(".-") or text.endswith(",-"):
        text = text[:-2] # 89.- becomes 89

    text = text.replace(",", ".") # decimal comma becomes a decimal point
    price: float = float(text)
    if math.isnan(price) or math.isinf(price): #float("nan") or float("inf") are valid floats but not valid prices
        raise ValueError("price is not a number")
    return price


def clean_cell(row: dict, column: str) -> str:
    # returns the cell as text without spaces around it, "" if the cell is empty or missing
    value: str | None = row.get(column)
    if value is None:
        return ""
    return value.strip()


def decode_bytes(data: bytes, name: str) -> str:
    # turns the raw bytes of a file into text, trying the encodings shop exports use
    # utf-8-sig = utf-8, and also removes the invisible mark Excel puts at the start of the file
    # cp1252 = older Windows / Excel exports (accents like "café" are stored differently)
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass # not utf-8, try the next one
    try:
        return data.decode("cp1252")
    except UnicodeDecodeError:
        raise LoaderError(f"Cannot read {name}: save it as CSV UTF-8 and try again")

#main function
def load_products_from_text(text: str) -> tuple[list[Product], list[str]]:
    # the web page gives the file as text: an uploaded file has no path
    products: list[Product] = []
    errors: list[str] = []
    line_of_id: dict[str, int] = {} # remembers on which line each id was first seen

    first_line: str = text.splitlines()[0] if text else ""
    delimiter: str = ";" if ";" in first_line else "," # some shops export semicolon
    reader: csv.DictReader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    header: list[str] = []
    if reader.fieldnames is not None:
        for name in reader.fieldnames:
            header.append(name.strip().lower()) # ignore capitals and spaces in the header
    reader.fieldnames = header # the DictReader will use the cleaned names

    missing: list[str] = []
    for column in REQUIRED_COLUMNS:
        if column not in header:
            missing.append(column)
    if len(missing) > 0:
        missing.sort()
        raise LoaderError(f"Missing columns: {', '.join(missing)}")

    # a description in quotes can go over several lines, so one row is not always one line
    # reader.line_num = the last line read in the file, after each row
    last_line: int = reader.line_num # the header
    for row in reader:
        line_number: int = last_line + 1 # the line where this row starts
        last_line = reader.line_num

        product_id: str = clean_cell(row, "id")
        if product_id == "":
            errors.append(f"Line {line_number}: missing id")
            continue

        if product_id in line_of_id:
            errors.append(f"Line {line_number}: duplicate id {product_id} (already on line {line_of_id[product_id]})")
            continue

        try:
            price: float | None = parse_price(row.get("price"))
        except ValueError:
            errors.append(f"Line {line_number}: price is not a number")
            continue

        product: Product = Product(
            id=product_id,
            category=clean_cell(row, "category"),
            title=clean_cell(row, "title"),
            description=clean_cell(row, "description"),
            price=price,
            currency=clean_cell(row, "currency"),
            availability=clean_cell(row, "availability"),
            gtin=clean_cell(row, "gtin"),
            brand=clean_cell(row, "brand"),
            image_url=clean_cell(row, "image_url"),
            attributes=clean_cell(row, "attributes"),
        )
        products.append(product)
        line_of_id[product_id] = line_number # only rows we keep

    return products, errors
