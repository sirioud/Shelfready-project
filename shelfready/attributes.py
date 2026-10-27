# Small tool to read the text of a listing. The rules use them.

import re

from .sector import ATTRIBUTE_LABELS

# attributes are written like this: "volume_l: 30 | material: nylon"
PAIR_SEPARATOR: str = "|"
KEY_VALUE_SEPARATOR: str = ":"

# a number followed by a unit: 30 l, 900 g, 750 ml, 400 lm, 20 h, 3 min, -8 °C
# the minus sign is only kept when it is not stuck to a word, so "2-person" stays positive
NUMBER_WITH_UNIT: re.Pattern = re.compile(
    r"((?:(?<![\w-])[-−])?\d+(?:[.,]\d+)?)\s*(°\s?c|minutes|min|ml|lm|l|g|kg|cm|mm|in|h|w|wh)(?![\w])", re.IGNORECASE
)
# a number on its own, not stuck to a letter (p001) or part of a decimal (12.5)
# a full stop after it is fine: "aged 6 to 10." still finds 10
BARE_NUMBER: re.Pattern = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?(?!\w|[.,]\d)")
# "pack of 4", "set of 6", "box of 2"
QUANTITY_PHRASE: re.Pattern = re.compile(r"\b(?:pack|set|box)\s+of\s+(\d+)\b", re.IGNORECASE)

# which unit belongs to which attribute key
UNIT_OF_KEY: dict[str, str] = {
    "capacity_ml": "ml",
    "volume_l": "l",
    "weight_g": "g",
    "length_cm": "cm",
    "laptop_in": "in",
    "battery_h": "h",
    "runtime_h": "h",
    "power_w": "w",
    "lumens_lm": "lm",
    "comfort_c": "°c",
    "limit_c": "°c",
    "extreme_c": "°c",
}


def parse_attributes(raw: str | None) -> dict[str, str]:
    # "volume_l: 30 | material: nylon" -> {"volume_l": "30", "material": "nylon"}
    pairs: dict[str, str] = {}
    if raw is None:
        return pairs

    chunks: list[str] = raw.split(PAIR_SEPARATOR)
    for chunk in chunks:
        if KEY_VALUE_SEPARATOR not in chunk:
            continue # no colon, not a key: value pair

        parts: list[str] = chunk.split(KEY_VALUE_SEPARATOR, 1) # split on the first colon only
        key: str = parts[0].strip().lower()
        value: str = parts[1].strip()
        if key != "" and value != "":
            pairs[key] = value
    return pairs


def specs_in_text(text: str | None) -> list[tuple[str, str]]:
    # finds every "number + unit" in free text, e.g. [("750", "ml"), ("900", "g")]
    found: list[tuple[str, str]] = []
    if text is None:
        return found

    matches: list[tuple[str, str]] = NUMBER_WITH_UNIT.findall(text)
    for match in matches:
        value: str = match[0].replace(",", ".").replace("−", "-") # "−" is the typographic minus sign
        unit: str = match[1].lower()
        unit = re.sub(r"\s", "", unit) # "° c" and "°c" are the same unit
        found.append((value, unit))
    return found


def bare_numbers(text: str | None) -> list[str]:
    # numbers with nothing to say what they are, e.g. "under 75" -> 75 what?
    found: list[str] = []
    if text is None:
        return found

    # positions of numbers that are fine because a unit or "pack of" explains them
    covered: list[int] = []
    for match in NUMBER_WITH_UNIT.finditer(text):
        start: int = match.start(1)
        if text[start] == "-" or text[start] == "−":
            start = start + 1 # the number itself starts after the minus sign
        covered.append(start)
    for match in QUANTITY_PHRASE.finditer(text):
        covered.append(match.start(1))

    for match in BARE_NUMBER.finditer(text):
        if match.start() in covered:
            continue

        next_characters: str = text[match.end():match.end() + 2]
        if next_characters.startswith("%") or next_characters.startswith("€") or next_characters.startswith("$"):
            continue # a percentage or a price is fine

        found.append(match.group())
    return found


# a number at the very start of a text: "30", "-8", "1.5"
LEADING_NUMBER: re.Pattern = re.compile(r"-?\d+(?:\.\d+)?")


def to_number(value: str) -> float | None:
    # "1100" -> 1100.0, "-2" -> -2.0, "1,5" -> 1.5, "30 l" -> 30.0, "30l" -> 30.0, "light" -> None
    text: str = value.strip().replace(",", ".").replace("−", "-")
    match: re.Match | None = LEADING_NUMBER.match(text)
    if match is None:
        return None
    return float(match.group())


def plain_name(key: str) -> str:
    # "limit_c" -> "limit temperature in °C (limit_c)", the key stays so the owner knows what to type
    if key in ATTRIBUTE_LABELS:
        return f"{ATTRIBUTE_LABELS[key]} ({key})"
    return key
