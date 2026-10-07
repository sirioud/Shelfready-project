"""The eleven AI-readability rules.
Every rule takes one Product and gives back one RuleResult."""

import re

from .attributes import UNIT_OF_KEY, bare_numbers, parse_attributes, plain_name, specs_in_text, to_number
from .models import Product, RuleResult
from .sector import (
    AVAILABILITY_VALUES,
    DECREASING_ATTRIBUTES,
    DEFAULT_EXPECTED,
    EXPECTED_ATTRIBUTES,
    PLACEHOLDER_BRANDS,
    PLAUSIBLE_RANGES,
)

MIN_ATTRIBUTES: int = 3 # a listing needs at least 3 attributes to be compared
PREMIUM_PRICE: float = 100.0 # from this price, a short description looks suspicious
MIN_PREMIUM_DESCRIPTION: int = 120 # characters
MIN_STRUCTURED_SHARE: float = 0.5 # at least half the specs in the description must also be attributes

PACK_PATTERN: re.Pattern = re.compile(r"\b(?:pack|set|box)\s+of\s+(\d+)\b", re.IGNORECASE)
# "compatible with ..." up to the full stop. "helmet-compatible hood" is a description, not a claim
COMPATIBILITY_PATTERN: re.Pattern = re.compile(r"\bcompatible\s+with\b[^.]*", re.IGNORECASE)
# a model name like "Primus 2", a size like "15 in", or a brand in capitals like "MSR"
MODEL_PATTERN: re.Pattern = re.compile(r"\b(?:[A-Z][A-Za-z]+\s?\d|\d+\s?(?:in|mm|cm)|[A-Z]{2,})\b")
CURRENCY_PATTERN: re.Pattern = re.compile(r"^[A-Z]{3}$") # EUR, CHF, USD

# points per rule, total = 100
# example values, to change once the scoring is decided
POINTS: dict[str, int] = {
    "expected_attributes": 20,
    "attribute_count": 5,
    "units": 12,
    "compatibility": 8,
    "quantity": 5,
    "gtin": 10,
    "feed_standard": 10,
    "price_coherence": 5,
    "spec_agreement": 10,
    "plausible_values": 5,
    "structured_share": 10,
}


def make_result(rule: str, passed: bool, message: str) -> RuleResult:
    # full points if the rule passed, 0 otherwise. the message is only kept when it failed
    if passed:
        return RuleResult(rule, True, POINTS[rule], "")
    return RuleResult(rule, False, 0, message)


def expected_for(category: str) -> list[str]:
    # the attributes this category must have
    key: str = category.strip().lower()
    if key in EXPECTED_ATTRIBUTES:
        return EXPECTED_ATTRIBUTES[key]
    return DEFAULT_EXPECTED


# criterion 1: distinctive attributes

def check_expected_attributes(product: Product) -> RuleResult:
    expected: list[str] = expected_for(product.category)
    found: dict[str, str] = parse_attributes(product.attributes)
    missing: list[str] = []
    for key in expected:
        if key not in found:
            missing.append(plain_name(key))
    passed: bool = len(missing) == 0
    return make_result("expected_attributes", passed, f"Missing for this category: {', '.join(missing)}")


def check_attribute_count(product: Product) -> RuleResult:
    found: dict[str, str] = parse_attributes(product.attributes)
    passed: bool = len(found) >= MIN_ATTRIBUTES
    return make_result("attribute_count", passed, f"Fewer than {MIN_ATTRIBUTES} structured attributes")


# criterion 2: disambiguation

def check_units(product: Product) -> RuleResult:
    text: str = product.title + " " + product.description
    loose: list[str] = bare_numbers(text)
    passed: bool = len(loose) == 0
    return make_result("units", passed, f"Number without a unit: {', '.join(loose[:3])}")


def check_compatibility(product: Product) -> RuleResult:
    # "compatible with most cartridges" is vague, "compatible with Primus 2" is not
    text: str = product.title + " " + product.description
    claims: list[str] = COMPATIBILITY_PATTERN.findall(text)
    vague: list[str] = []
    for claim in claims:
        if MODEL_PATTERN.search(claim) is None:
            vague.append(claim)
    passed: bool = len(vague) == 0
    return make_result("compatibility", passed, "Compatibility claim without a precise list of models")


def check_quantity(product: Product) -> RuleResult:
    # "pack of 2" in the text needs a pack_size attribute
    text: str = product.title + " " + product.description
    match: re.Match | None = PACK_PATTERN.search(text)
    found: dict[str, str] = parse_attributes(product.attributes)
    passed: bool = match is None or "pack_size" in found
    return make_result("quantity", passed, "Pack mentioned but the " + plain_name("pack_size") + " is missing")


def is_valid_gtin(code: str) -> bool:
    # GS1 check digit: from the right, multiply the digits by 3, 1, 3, 1...
    # the last digit must bring the total up to the next multiple of 10
    if not code.isdigit():
        return False
    valid_lengths: list[int] = [8, 12, 13, 14]
    if len(code) not in valid_lengths:
        return False

    digits: list[int] = []
    for character in code:
        digits.append(int(character))
    check_digit: int = digits.pop() # remove the last digit, it is the one we check

    total: int = 0
    position: int = 0
    for index in range(len(digits) - 1, -1, -1): # walk from right to left
        weight: int = 1
        if position % 2 == 0:
            weight = 3
        total = total + digits[index] * weight
        position = position + 1

    expected: int = (10 - total % 10) % 10
    return expected == check_digit


def check_gtin(product: Product) -> RuleResult:
    passed: bool = is_valid_gtin(product.gtin)
    return make_result("gtin", passed, "Barcode (GTIN) missing or invalid")


def check_feed_standard(product: Product) -> RuleResult:
    # values must follow the google merchant center specification
    # a listing that fails this rule would be rejected by the feed, so scoring.py blocks it
    problems: list[str] = []

    if product.title.strip() == "":
        problems.append("title is empty")

    if product.price is None or product.price <= 0:
        problems.append("price is missing")

    availability: str = product.availability.strip().lower().replace(" ", "_") # "in stock" -> "in_stock"
    if availability not in AVAILABILITY_VALUES:
        problems.append(f"availability '{product.availability}' is not an accepted value")

    if CURRENCY_PATTERN.match(product.currency) is None:
        problems.append("currency is not a three-letter code")

    brand: str = product.brand.strip().lower()
    if brand == "" or brand in PLACEHOLDER_BRANDS:
        problems.append("brand is empty or a placeholder")

    passed: bool = len(problems) == 0
    return make_result("feed_standard", passed, "; ".join(problems))


# criterion 3: price / content coherence

def check_price_coherence(product: Product) -> RuleResult:
    # an expensive product with a very short description is not credible
    if product.price is None or product.price < PREMIUM_PRICE:
        return make_result("price_coherence", True, "")
    passed: bool = len(product.description) >= MIN_PREMIUM_DESCRIPTION
    return make_result("price_coherence", passed, f"Premium price but description shorter than {MIN_PREMIUM_DESCRIPTION} characters")


def check_spec_agreement(product: Product) -> RuleResult:
    # title says 25 l but the attribute says volume_l: 30 -> contradiction
    found: dict[str, str] = parse_attributes(product.attributes)
    conflicts: list[str] = []
    for value, unit in specs_in_text(product.title):
        # attributes of this listing that use the same unit
        # a sleeping bag has three in °C (comfort, limit, extreme), so the title only has to agree with one
        same_unit: list[str] = []
        for key in UNIT_OF_KEY:
            if UNIT_OF_KEY[key] == unit and key in found:
                same_unit.append(key)
        if len(same_unit) == 0:
            continue # no attribute to compare with

        # compare as numbers, so "30", "30.0" and "30 l" are the same value
        title_number: float | None = to_number(value)
        agrees: bool = False
        for key in same_unit:
            if to_number(found[key]) == title_number:
                agrees = True

        if not agrees:
            values: list[str] = []
            for key in same_unit:
                values.append(f"{plain_name(key)} is {found[key]}")
            conflicts.append(f"title says {value} {unit} but {', '.join(values)}")
    passed: bool = len(conflicts) == 0
    return make_result("spec_agreement", passed, f"Title contradicts an attribute: {'; '.join(conflicts[:2])}")


def show_number(number: float) -> str:
    # 1500.0 -> "1500", 1.5 -> "1.5"
    if number == int(number):
        return str(int(number))
    return str(number)


def check_plausible_values(product: Product) -> RuleResult:
    # the numbers must make sense: no weight of 1.2 g for a sleeping bag, no comfort colder than the limit
    found: dict[str, str] = parse_attributes(product.attributes)
    problems: list[str] = []

    # 1. each number inside its usual range
    for key in PLAUSIBLE_RANGES:
        if key not in found:
            continue
        number: float | None = to_number(found[key])
        if number is None:
            problems.append(f"{plain_name(key)} should be a number, not '{found[key]}'")
            continue
        lowest: int = PLAUSIBLE_RANGES[key][0]
        highest: int = PLAUSIBLE_RANGES[key][1]
        if number < lowest or number > highest:
            problems.append(f"{plain_name(key)} is {found[key]}, outside the usual range ({lowest} to {highest})")

    # 2. temperatures that must go down: comfort > limit > extreme
    for group in DECREASING_ATTRIBUTES:
        previous_key: str = ""
        previous_number: float | None = None
        for key in group:
            if key not in found:
                continue
            number = to_number(found[key])
            if number is None:
                continue
            if previous_number is not None and number >= previous_number:
                problems.append(f"{plain_name(key)} is {show_number(number)}, it should be lower than the {plain_name(previous_key)} ({show_number(previous_number)})")
            previous_key = key
            previous_number = number

    passed: bool = len(problems) == 0
    return make_result("plausible_values", passed, "Implausible value: " + "; ".join(problems[:2]))


# criterion 4: structuring

def structured_share(product: Product) -> float:
    # share of the specs in the description that are also written as attributes, 0.0 to 1.0
    found: dict[str, str] = parse_attributes(product.attributes)
    in_text: list[tuple[str, str]] = specs_in_text(product.description)

    if len(in_text) == 0:
        # nothing to compare: fine if there are attributes, bad if there are none
        if len(found) > 0:
            return 1.0
        return 0.0

    # every number written in the attributes, e.g. [30.0, 900.0]
    attribute_numbers: list[float] = []
    for attribute in found.values():
        number: float | None = to_number(attribute)
        if number is not None:
            attribute_numbers.append(number)

    # compare as numbers, so "30" in the text and "30.0" in the attributes are the same value
    covered: int = 0
    for value, unit in in_text:
        if to_number(value) in attribute_numbers:
            covered = covered + 1
    return covered / len(in_text)


def check_structured_share(product: Product) -> RuleResult:
    share: float = structured_share(product)
    passed: bool = share >= MIN_STRUCTURED_SHARE
    return make_result("structured_share", passed, "Specifications live in the description instead of structured attributes")


# all rules, in the order they run. to add a rule: write it, add it here and in POINTS
ALL_RULES: list = [
    check_expected_attributes,
    check_attribute_count,
    check_units,
    check_compatibility,
    check_quantity,
    check_gtin,
    check_feed_standard,
    check_price_coherence,
    check_spec_agreement,
    check_plausible_values,
    check_structured_share,
]
