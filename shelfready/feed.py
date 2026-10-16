"""AI-ready feed: a google merchant center supplemental feed made from the shop's own data.
Two "conversational attributes" that AI Mode and Gemini read:
- product_highlight: the specs as short facts, e.g. "Volume: 30 l"
- question_and_answer: the shopper questions this listing can answer, e.g. "Is it warm enough for a night at -5 °C?"
Nothing is invented: every value comes from the attributes column. No AI is used.
The file is tab separated (TSV), so a comma inside a value cannot split it."""

from pathlib import Path

from .attributes import Unit_of_key, to_number
from .models import Product
from .questions import No, Yes, answer_question, questions_for
from .rules import check_plausible_values, check_spec_agreement
from .sector import Attribute_labels, Feed_question_wording

Feed_columns: list[str] = ["id", "product_highlight", "question_and_answer"]
Min_highlights: int = 2 # google merchant center asks for at least 2 highlights
Max_highlights: int = 10
Max_highlight_length: int = 150 # characters, google merchant center limit


def short_label(key: str) -> str:
    # "volume in litres" -> "Volume", "size system: EU, US or UK" -> "Size system", "limit_c" stays "limit_c"
    label: str = key
    if key in Attribute_labels:
        label = Attribute_labels[key]
    label = label.split(":")[0]
    label = label.split(" in ")[0]
    return label[0].upper() + label[1:]


def with_unit(key: str, value: str) -> str:
    # "30" with volume_l -> "30 l", "-8" with limit_c -> "-8 °C", "nylon" stays "nylon"
    if key not in Unit_of_key:
        return value
    if to_number(value) is None:
        return value
    if value.replace(".", "").replace("-", "").replace(",", "").isdigit():
        unit: str = Unit_of_key[key].replace("°c", "°C").replace("w", "W")
        return f"{value} {unit}"
    return value # the value already has its unit, e.g. "30 l"


def clean(text: str) -> str:
    # no tabs or new lines (they would break the file) and no double quotes (they mark the values)
    return text.replace("\t", " ").replace("\n", " ").replace('"', "'")


def highlights_of(product: Product) -> list[str]:
    # one highlight per attribute, e.g. ["Volume: 30 l", "Weight: 900 g", "Material: nylon"]
    found: dict[str, str] = product.attrs()
    highlights: list[str] = []
    for key in found:
        highlight: str = f"{short_label(key)}: {with_unit(key, found[key])}"
        if len(highlight) <= Max_highlight_length:
            highlights.append(clean(highlight))
    if len(highlights) < Min_highlights:
        return [] # too few to send, google would refuse the attribute
    return highlights[:Max_highlights]


def questions_and_answers(product: Product) -> list[tuple[str, str]]:
    # the shopper questions this listing can answer with yes or no
    # e.g. [("Is it warm enough for a night at -5 °C?", "Yes, limit temperature is -8 °C.")]
    # a question the listing cannot answer (attribute missing) is left out: we never guess
    found: dict[str, str] = product.attrs()
    pairs: list[tuple[str, str]] = []
    for question in questions_for(product.category):
        answer: str = answer_question(product, question)
        if answer != Yes and answer != No:
            continue

        text: str = question[0]
        if text in Feed_question_wording:
            text = Feed_question_wording[text]

        key: str = question[1]
        start: str = "Yes"
        if answer == No:
            start = "No"
        reply: str = f"{start}, {short_label(key).lower()} is {with_unit(key, found[key])}."
        pairs.append((clean(text), clean(reply)))
    return pairs


def feed_row(product: Product) -> list[str]:
    # one line of the feed: id, highlights, questions and answers
    # each value is in double quotes and the values are separated by commas, as google asks
    highlights: list[str] = []
    for highlight in highlights_of(product):
        highlights.append(f'"{highlight}"')

    answers: list[str] = []
    for question, reply in questions_and_answers(product):
        answers.append(f'"{question}":"{reply}"')

    return [clean(product.id), ", ".join(highlights), ", ".join(answers)]


def can_be_sent(product: Product) -> bool:
    # values that contradict the title or look wrong must be fixed first, not sent to google
    return check_spec_agreement(product).passed and check_plausible_values(product).passed


def supplemental_feed(products: list[Product]) -> str:
    # the whole feed as text, one line per product that has something to add
    lines: list[str] = ["\t".join(Feed_columns)]
    for product in products:
        if not can_be_sent(product):
            continue
        row: list[str] = feed_row(product)
        if row[1] == "" and row[2] == "":
            continue # nothing to add for this product
        lines.append("\t".join(row))
    return "\n".join(lines) + "\n"


def write_supplemental_feed(path: str | Path, products: list[Product]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(supplemental_feed(products), encoding="utf-8")
    return path
