# Knowledge about the industry, kept as plain data. Sector: outdoor and sport gear.
# To audit another sector, change this file and the sample csv. The rules do not change.

SECTOR: str = "Outdoor and sport gear"

# google merchant center asks for these on clothing and shoes (size_system is recommended)
APPAREL: list[str] = ["size", "size_system", "color", "gender", "age_group"]

# attributes each category must have
EXPECTED_ATTRIBUTES: dict[str, list[str]] = {
    "backpack": ["volume_l", "weight_g", "material"],
    # EN ISO 23537: a sleeping bag is labelled with comfort, limit and extreme temperature
    "sleeping_bag": ["comfort_c", "limit_c", "extreme_c", "weight_g"],
    "headlamp": ["lumens_lm", "runtime_h", "weight_g"],
    "bottle": ["capacity_ml", "weight_g", "material"],
    "stove": ["power_w", "fuel", "weight_g"],
    "shoes": APPAREL,
    "socks": APPAREL,
}
# used when the category is not in the list above
DEFAULT_EXPECTED: list[str] = ["material"]

# what each attribute key means, for the reports
ATTRIBUTE_LABELS: dict[str, str] = {
    "volume_l": "volume in litres",
    "weight_g": "weight in grams",
    "material": "material",
    "comfort_c": "comfort temperature in °C",
    "limit_c": "limit temperature in °C",
    "extreme_c": "extreme temperature in °C",
    "lumens_lm": "brightness in lumens",
    "runtime_h": "battery runtime in hours",
    "battery_h": "battery life in hours",
    "capacity_ml": "capacity in ml",
    "power_w": "power in watts",
    "fuel": "fuel type",
    "length_cm": "length in cm",
    "laptop_in": "laptop size in inches",
    "size": "size",
    "size_system": "size system: EU, US or UK",
    "color": "colour",
    "gender": "gender: male, female or unisex",
    "age_group": "age group: adult or kids",
    "pack_size": "number of items in the pack",
}

# values accepted by the shopping feed (google merchant center)
AVAILABILITY_VALUES: set[str] = {"in_stock", "out_of_stock", "preorder", "backorder"}
# brand names that mean "no brand"
PLACEHOLDER_BRANDS: set[str] = {"n/a", "na", "none", "generic", "no brand", "unknown"}

# usual range for each number, [lowest, highest]. a value outside is probably a typo or a wrong unit
# e.g. weight_g: 1.2 is a sleeping bag weight written in kg instead of g
PLAUSIBLE_RANGES: dict[str, list[int]] = {
    "weight_g": [5, 10000],
    "volume_l": [1, 120],
    "capacity_ml": [50, 5000],
    "lumens_lm": [5, 5000],
    "runtime_h": [1, 500],
    "power_w": [500, 10000],
    "comfort_c": [-40, 25],
    "limit_c": [-50, 20],
    "extreme_c": [-70, 15],
}

# attributes that must go down from left to right
# EN ISO 23537: comfort temperature > limit temperature > extreme temperature
DECREASING_ATTRIBUTES: list[list[str]] = [
    ["comfort_c", "limit_c", "extreme_c"],
]

# typical questions a shopper asks an AI assistant, per category
# each question is: (what the shopper asks, attribute needed, test, value)
# tests: "at_least", "at_most", "equals"
# if the listing does not have the attribute, the assistant cannot match it to the question
SHOPPER_QUESTIONS: dict[str, list[tuple]] = {
    "backpack": [
        ("A backpack of 30 l or more for a weekend", "volume_l", "at_least", 30),
        ("A backpack under 1 kg", "weight_g", "at_most", 1000),
    ],
    "sleeping_bag": [
        ("A sleeping bag for a night at -5 °C", "limit_c", "at_most", -5),
        ("A sleeping bag under 1.5 kg", "weight_g", "at_most", 1500),
    ],
    "headlamp": [
        ("A headlamp of 300 lm or more", "lumens_lm", "at_least", 300),
        ("A headlamp that lasts 8 h or more", "runtime_h", "at_least", 8),
    ],
    "bottle": [
        ("A bottle of 750 ml or more", "capacity_ml", "at_least", 750),
        ("A bottle under 200 g", "weight_g", "at_most", 200),
    ],
    "stove": [
        ("A stove under 100 g", "weight_g", "at_most", 100),
    ],
    "shoes": [
        ("Shoes in EU size 42", "size", "equals", "42"),
        ("Unisex shoes", "gender", "equals", "unisex"),
    ],
}
# for aisearch test:
# needs a shopper describes to an AI assistant, for the AI search test (ai_search.py), one per category
# same shape as SHOPPER_QUESTIONS, so answer_question() works on them: the text is what the shopper
# wants to do, the attribute / test / value is the spec that proves a product fits that need
NEED_QUESTIONS: dict[str, list[tuple]] = {
    "backpack": [("A backpack for a weekend hut-to-hut hike", "volume_l", "at_least", 30)],
    "sleeping_bag": [("A sleeping bag for a winter night in the Alps", "limit_c", "at_most", -5)],
    "headlamp": [("A headlamp for night trail running", "lumens_lm", "at_least", 300)],
    "bottle": [("A bottle with enough water for a long day hike", "capacity_ml", "at_least", 750)],
    "stove": [("A stove for ultralight trekking", "weight_g", "at_most", 100)],
}

# GEO (generative engine optimization): AI assistants quote facts, not marketing claims
# Aggarwal et al., KDD 2024: numbers raise visibility, an authoritative tone does not
MARKETING_WORDS: list[str] = [
    "premium", "ultimate", "best", "best-in-class", "revolutionary", "innovative",
    "high-quality", "high quality", "top quality", "world-class", "unbeatable", "amazing",
    "perfect", "incredible", "exceptional", "state-of-the-art", "cutting-edge", "must-have",
    "superior", "unique", "legendary", "game-changing",
]

# words that say what the product is, per category. the description must start with one of them
CATEGORY_WORDS: dict[str, list[str]] = {
    "backpack": ["backpack", "daypack", "rucksack", "pack"],
    "sleeping_bag": ["sleeping bag", "quilt"],
    "headlamp": ["headlamp", "head lamp", "head torch"],
    "bottle": ["bottle", "flask"],
    "stove": ["stove", "burner"],
    "shoes": ["shoe", "shoes", "boot", "boots", "trainer", "trainers", "sneakers"],
    "socks": ["sock", "socks"],
}

# shopper questions written as a question, for the AI-ready feed (question_and_answer in google merchant center)
FEED_QUESTION_WORDING: dict[str, str] = {
    "A backpack of 30 l or more for a weekend": "Is it big enough for a weekend (30 l or more)?",
    "A backpack under 1 kg": "Does it weigh less than 1 kg?",
    "A sleeping bag for a night at -5 °C": "Is it warm enough for a night at -5 °C?",
    "A sleeping bag under 1.5 kg": "Does it weigh less than 1.5 kg?",
    "A headlamp of 300 lm or more": "Does it give 300 lm or more?",
    "A headlamp that lasts 8 h or more": "Does the battery last 8 h or more?",
    "A bottle of 750 ml or more": "Does it hold 750 ml or more?",
    "A bottle under 200 g": "Does it weigh less than 200 g?",
    "A stove under 100 g": "Does it weigh less than 100 g?",
    "Shoes in EU size 42": "Is it EU size 42?",
    "Unisex shoes": "Is it unisex?",
}
