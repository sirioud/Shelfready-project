#Shopper questions (list in sector.py), e.g. "a sleeping bag for a night at -5 °C".
#For each listing: yes, no, or unknown when the attribute is missing.
#Unknown = the assistant can never show the listing for that question. Not part of the score."""

from .attributes import plain_name, to_number
from .models import Product
from .sector import SHOPPER_QUESTIONS

YES: str = "yes"
NO: str = "no"
UNKNOWN: str = "unknown"


def questions_for(category: str) -> list[tuple]:
    # the questions for this category, empty list if the category has none
    key: str = category.strip().lower()
    if key in SHOPPER_QUESTIONS:
        return SHOPPER_QUESTIONS[key]
    return []


def answer_question(product: Product, question: tuple) -> str:
    # question = (text, attribute, test, wanted value), see sector.py
    attribute: str = question[1]
    test: str = question[2]
    wanted = question[3] # a number for at_least / at_most, a text for equals
    found: dict[str, str] = product.attrs()

    if attribute not in found:
        return UNKNOWN

    if test == "equals":
        if found[attribute].lower() == str(wanted).lower():
            return YES
        return NO

    # "at_least" and "at_most" need a number
    number: float | None = to_number(found[attribute])
    if number is None:
        return UNKNOWN
    if test == "at_least" and number >= wanted:
        return YES
    if test == "at_most" and number <= wanted:
        return YES
    return NO


def unanswered_questions(product: Product) -> list[str]:
    # the questions this listing cannot be matched to, with the missing attribute
    # e.g. ["A sleeping bag for a night at -5 °C: needs the limit temperature in °C (limit_c)"]
    missing: list[str] = []
    for question in questions_for(product.category):
        if answer_question(product, question) == UNKNOWN:
            missing.append(f"{question[0]}: needs the {plain_name(question[1])}")
    return missing


def question_summary(products: list[Product]) -> list[dict]:
    # one entry per question asked in this catalog, with the ids that match and the ids that cannot be matched
    summary: list[dict] = []
    for category in SHOPPER_QUESTIONS:
        # only the products of this category
        in_category: list[Product] = []
        for product in products:
            if product.category.strip().lower() == category:
                in_category.append(product)
        if len(in_category) == 0:
            continue # nobody in the catalog sells this category

        for question in SHOPPER_QUESTIONS[category]:
            matches: list[str] = []
            unknown: list[str] = []
            for product in in_category:
                answer: str = answer_question(product, question)
                if answer == YES:
                    matches.append(product.id)
                elif answer == UNKNOWN:
                    unknown.append(product.id)
            summary.append({"question": question[0], "matches": matches, "unknown": unknown})
    return summary
