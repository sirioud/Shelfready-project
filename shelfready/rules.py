#The fourteen AI-readability rules.
#Every rule takes one Product and gives back one RuleResult."""

import re

from .attributes import QUANTITY_PHRASE, UNIT_OF_KEY, bare_numbers, plain_name, specs_in_text, to_number
from .models import Product, RuleResult
from .sector import (
    AVAILABILITY_VALUES,
    CATEGORY_WORDS,
    DECREASING_ATTRIBUTES,
    DEFAULT_EXPECTED,
    EXPECTED_ATTRIBUTES,
    MARKETING_WORDS,
    PLACEHOLDER_BRANDS,
    PLAUSIBLE_RANGES,
)

MIN_ATTRIBUTES: int = 3 # a listing needs at least 3 attributes to be compared
PREMIUM_PRICE: float = 100.0 # from this price, a short description looks suspicious
MIN_PREMIUM_DESCRIPTION: int = 120 # characters
MIN_STRUCTURED_SHARE: float = 0.5 # at least half the specs in the description must also be attributes

# "compatible with ..." up to the full stop. "helmet-compatible hood" is a description, not a claim
COMPATIBILITY_PATTERN: re.Pattern = re.compile(r"\bcompatible\s+with\b[^.]*", re.IGNORECASE)
# a model name like "Primus 2", a size like "15 in", or a brand in capitals like "MSR"
MODEL_PATTERN: re.Pattern = re.compile(r"\b(?:[A-Z][A-Za-z]+\s?\d|\d+\s?(?:in|mm|cm)|[A-Z]{2,})\b")
CURRENCY_PATTERN: re.Pattern = re.compile(r"^[A-Z]{3}$") # EUR, CHF, USD

MIN_CLAIMS: int = 2 # from 2 marketing words, the description needs as many numbers
MAX_TITLE_LENGTH: int = 150 # google merchant center cuts titles after 150 characters
MIN_WORD_LENGTH: int = 4 # shorter words ("of", "and", "for") can repeat in a normal title
MAX_TITLE_COMMAS: int = 3 # "backpack, hiking, camping, travel" is a list of keywords, not a title
WORD_PATTERN: re.Pattern = re.compile(r"[a-zA-Z]+")

# POINTS, ALL_RULES and CRITERION_OF_RULE are all built from RULE_REGISTRY at the end of this file,
# so each rule is declared in exactly one place. make_result reads POINTS when a rule actually runs,
# which is after the module has finished loading, so defining it below is fine.


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
    found: dict[str, str] = product.attrs()
    missing: list[str] = []
    for key in expected:
        if key not in found:
            missing.append(plain_name(key))
    passed: bool = len(missing) == 0
    return make_result("expected_attributes", passed, f"Missing for this category: {', '.join(missing)}")


def check_attribute_count(product: Product) -> RuleResult:
    found: dict[str, str] = product.attrs()
    passed: bool = len(found) >= MIN_ATTRIBUTES
    return make_result("attribute_count", passed, f"Fewer than {MIN_ATTRIBUTES} structured attributes")


# criterion 2: disambiguation

def check_units(product: Product) -> RuleResult:
    text: str = product.text()
    loose: list[str] = bare_numbers(text)
    passed: bool = len(loose) == 0
    return make_result("units", passed, f"Number without a unit: {', '.join(loose[:3])}")


def check_compatibility(product: Product) -> RuleResult:
    # "compatible with most cartridges" is vague, "compatible with Primus 2" is not
    text: str = product.text()
    claims: list[str] = COMPATIBILITY_PATTERN.findall(text)
    vague: list[str] = []
    for claim in claims:
        if MODEL_PATTERN.search(claim) is None:
            vague.append(claim)
    passed: bool = len(vague) == 0
    return make_result("compatibility", passed, "Compatibility claim without a precise list of models")


def check_quantity(product: Product) -> RuleResult:
    # "pack of 2" in the text needs a pack_size attribute
    text: str = product.text()
    match: re.Match | None = QUANTITY_PHRASE.search(text)
    found: dict[str, str] = product.attrs()
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

    # weight the remaining digits from right to left: 3, 1, 3, 1...
    digits.reverse()
    total: int = 0
    for position in range(len(digits)):
        weight: int = 1
        if position % 2 == 0:
            weight = 3
        total = total + digits[position] * weight

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

    if product.image_url.strip() == "":
        problems.append("image_url is empty")

    passed: bool = len(problems) == 0
    return make_result("feed_standard", passed, "; ".join(problems))


# criterion 3: price / content coherence

def check_price_coherence(product: Product) -> RuleResult:
    # an expensive product with a very short description is not credible
    if product.price is None or product.price < PREMIUM_PRICE:
        return make_result("price_coherence", True, "")
    passed: bool = len(product.description) >= MIN_PREMIUM_DESCRIPTION
    return make_result("price_coherence", passed, f"Premium price but description shorter than {MIN_PREMIUM_DESCRIPTION} characters")


def text_conflicts(text: str, found: dict[str, str], where: str) -> list[str]:
    # numbers in the text that disagree with the attribute of the same unit
    # e.g. "title says 25 l but volume in litres (volume_l) is 30"
    conflicts: list[str] = []
    for value, unit in specs_in_text(text):
        # attributes of this listing that use the same unit
        # a sleeping bag has three in °C (comfort, limit, extreme), so the text only has to agree with one
        same_unit: list[str] = []
        for key in UNIT_OF_KEY:
            if UNIT_OF_KEY[key] == unit and key in found:
                same_unit.append(key)
        if len(same_unit) == 0:
            continue # no attribute to compare with

        # compare as numbers, so "30", "30.0" and "30 l" are the same value
        text_number: float | None = to_number(value)
        agrees: bool = False
        for key in same_unit:
            if to_number(found[key]) == text_number:
                agrees = True

        if not agrees:
            values: list[str] = []
            for key in same_unit:
                values.append(f"{plain_name(key)} is {found[key]}")
            conflicts.append(f"{where} says {value} {unit} but {', '.join(values)}")
    return conflicts


def check_spec_agreement(product: Product) -> RuleResult:
    # title or description says 25 l but the attribute says volume_l: 30 -> contradiction
    found: dict[str, str] = product.attrs()
    conflicts: list[str] = text_conflicts(product.title, found, "title")
    conflicts = conflicts + text_conflicts(product.description, found, "description")
    passed: bool = len(conflicts) == 0
    return make_result("spec_agreement", passed, f"Text contradicts an attribute: {'; '.join(conflicts[:2])}")


def show_number(number: float) -> str:
    # 1500.0 -> "1500", 1.5 -> "1.5"
    if number == int(number):
        return str(int(number))
    return str(number)


def check_plausible_values(product: Product) -> RuleResult:
    # the numbers must make sense: no weight of 1.2 g for a sleeping bag, no comfort colder than the limit
    found: dict[str, str] = product.attrs()
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
    found: dict[str, str] = product.attrs()
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


# criterion 5: clear wording (GEO)

def marketing_words_in(text: str) -> list[str]:
    # the marketing words found in the text, e.g. ["premium", "ultimate"]
    found: list[str] = []
    lowered: str = text.lower()
    for word in MARKETING_WORDS:
        # \b = word boundary, so "best" is not found inside "bestseller"
        if re.search(r"\b" + re.escape(word) + r"\b", lowered) is not None:
            found.append(word)
    return found


def check_facts_not_claims(product: Product) -> RuleResult:
    # "ultra premium quality" tells an assistant nothing, "weighs 780 g" can be compared
    text: str = product.text()
    claims: list[str] = marketing_words_in(text)
    facts: int = len(specs_in_text(text))
    passed: bool = len(claims) < MIN_CLAIMS or facts >= len(claims)
    return make_result("facts_not_claims", passed, f"Marketing words instead of facts: {', '.join(claims[:4])}")


def check_keyword_stuffing(product: Product) -> RuleResult:
    # "Backpack hiking backpack camping backpack" -> the same word again and again
    problems: list[str] = []

    counts: dict[str, int] = {}
    for word in WORD_PATTERN.findall(product.title.lower()):
        if len(word) < MIN_WORD_LENGTH:
            continue
        if word in counts:
            counts[word] = counts[word] + 1
        else:
            counts[word] = 1
    repeated: list[str] = []
    for word in counts:
        if counts[word] > 1:
            repeated.append(word)
    if len(repeated) > 0:
        problems.append(f"repeated in the title: {', '.join(repeated)}")

    if product.title.count(",") >= MAX_TITLE_COMMAS:
        problems.append("the title is a list of keywords")

    if len(product.title) > MAX_TITLE_LENGTH:
        problems.append(f"the title is longer than {MAX_TITLE_LENGTH} characters")

    passed: bool = len(problems) == 0
    return make_result("keyword_stuffing", passed, "Keyword stuffing: " + "; ".join(problems))


def first_sentence(text: str) -> str:
    # the text up to the first full stop, "!" or "?"
    match: re.Match | None = re.search(r"[.!?](\s|$)", text)
    if match is None:
        return text
    return text[:match.start()]


def check_clear_opening(product: Product) -> RuleResult:
    # the first sentence must say what the product is: "Hiking daypack with...", not "Adventure awaits!"
    key: str = product.category.strip().lower()
    if key not in CATEGORY_WORDS:
        return make_result("clear_opening", True, "") # unknown category, nothing to compare with

    opening: str = first_sentence(product.description).lower()
    names_it: bool = False
    for word in CATEGORY_WORDS[key]:
        if re.search(r"\b" + re.escape(word) + r"\b", opening) is not None:
            names_it = True
    return make_result("clear_opening", names_it, f"The first sentence does not say what the product is (e.g. {CATEGORY_WORDS[key][0]})")


# the one place a rule is declared: its function, its points, and the criterion it scores.
# to add a rule: write the check_ function above, then add one line here. nothing else to keep in sync.
# the rule name used everywhere else is the function name without "check_" (check_gtin -> "gtin").
# total points = 100, split across the five criteria (see report.CRITERIA).
RULE_REGISTRY: list[tuple] = [
    (check_expected_attributes, 17, "Distinctive attributes"),
    (check_attribute_count, 4, "Distinctive attributes"),
    (check_units, 10, "Disambiguation"),
    (check_compatibility, 6, "Disambiguation"),
    (check_quantity, 5, "Disambiguation"),
    (check_gtin, 8, "Disambiguation"),
    (check_feed_standard, 10, "Disambiguation"),
    (check_price_coherence, 4, "Price / content coherence"),
    (check_spec_agreement, 9, "Price / content coherence"),
    (check_plausible_values, 4, "Price / content coherence"),
    (check_structured_share, 8, "Structuring"),
    (check_facts_not_claims, 6, "Clear wording"),
    (check_keyword_stuffing, 4, "Clear wording"),
    (check_clear_opening, 5, "Clear wording"),
]


def rule_name(check_function) -> str:
    # the name used as a key everywhere: check_gtin -> "gtin"
    return check_function.__name__.replace("check_", "")


# derived from the registry, so these three can never drift apart
ALL_RULES: list = [entry[0] for entry in RULE_REGISTRY] # the functions, in run order
POINTS: dict[str, int] = {rule_name(entry[0]): entry[1] for entry in RULE_REGISTRY}
CRITERION_OF_RULE: dict[str, str] = {rule_name(entry[0]): entry[2] for entry in RULE_REGISTRY}
