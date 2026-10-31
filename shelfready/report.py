# The report the web page offers for download, as a pdf file.

from datetime import date

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from .rules import POINTS, CRITERION_OF_RULE
from .questions import question_summary, unanswered_questions
from .scoring import ProductScore, count_ready, most_common_problems

# the five criteria, in display order. each rule is mapped to one of these in rules.RULE_REGISTRY
CRITERIA: list[str] = ["Distinctive attributes", "Disambiguation", "Price / content coherence", "Structuring", "Clear wording"]

# one example per criterion, shown under its score in the app and in the pdf report
CRITERION_EXAMPLE: dict[str, str] = {
    "Distinctive attributes": "e.g. a sleeping bag with no temperature rating",
    "Disambiguation": "e.g. \"weighs 75\" instead of \"weighs 75 g\"",
    "Price / content coherence": "e.g. the title says 25 l, the specs say 30 l",
    "Structuring": "e.g. \"400 lumens\" written only in the description",
    "Clear wording": "e.g. \"ultra-light\" instead of \"weighs 780 g\"",
}

# each rule in plain words, for shop owners
RULE_NAMES: dict[str, str] = {
    "expected_attributes": "Key specs missing",
    "attribute_count": "Too few specs",
    "units": "Number without a unit",
    "compatibility": "Vague compatibility",
    "quantity": "Pack size not given",
    "gtin": "Barcode missing or wrong",
    "feed_standard": "Rejected by Google Shopping",
    "price_coherence": "Description too short for the price",
    "spec_agreement": "Text and specs disagree",
    "plausible_values": "Value that looks wrong",
    "structured_share": "Specs hidden in the text",
    "facts_not_claims": "Marketing words instead of facts",
    "keyword_stuffing": "Keyword stuffing in the title",
    "clear_opening": "Unclear first sentence",
}

# what the shop owner can do about each problem
HOW_TO_FIX: dict[str, str] = {
    "expected_attributes": "Add the missing specs to the attributes column, e.g. the limit temperature for a sleeping bag.",
    "attribute_count": "Give at least 3 specs in the attributes column (weight, size, material...).",
    "units": "Write the unit after every number: 75 kg, not 75.",
    "compatibility": "Name the exact models it works with instead of 'most' or 'all'.",
    "quantity": "Add the number of items in the pack to the attributes.",
    "gtin": "Copy the barcode from the box. The last digit is a check digit, so one typo makes it invalid.",
    "feed_standard": "Fill in the title, the price and the image URL, set the availability to in stock, out of stock, preorder or backorder, and give a real brand.",
    "price_coherence": "Write a longer description: an expensive product needs at least 120 characters.",
    "spec_agreement": "Make the title, the description and the attributes say the same number.",
    "plausible_values": "Check the value and its unit: the weight is in grams, temperatures go comfort > limit > extreme.",
    "structured_share": "Copy the numbers from the description into the attributes column, e.g. the brightness in lumens.",
    "facts_not_claims": "Replace each claim with a number: 'ultra-light' becomes 'weighs 780 g'.",
    "keyword_stuffing": "Write the title as a name, each word once: brand, product type, key spec.",
    "clear_opening": "Start the description with what the product is and what it is for: 'Hiking daypack for day trips...'.",
}

# why each rule exists, shown in the pdf report
BASIS_OF_RULE: dict[str, str] = {
    "expected_attributes": "Sector profile: ISO 23537 ratings for sleeping bags, feed apparel attributes for footwear",
    "attribute_count": "AI comparison relies on several filterable attributes",
    "units": "Numbers without units cannot be compared",
    "compatibility": "Vague compatibility claims cannot be resolved",
    "quantity": "Unit versus pack must be explicit",
    "gtin": "GS1 check digit, required by shopping feeds",
    "feed_standard": "Google Merchant Center product data specification",
    "price_coherence": "Consistent product details",
    "spec_agreement": "Consistent product details",
    "plausible_values": "Sector value ranges; EN ISO 23537 order comfort > limit > extreme",
    "structured_share": "Facts in dedicated fields, as in Product structured data",
    "facts_not_claims": "GEO (Aggarwal et al., KDD 2024): statistics raise visibility in AI answers, an authoritative tone does not",
    "keyword_stuffing": "GEO (Aggarwal et al., KDD 2024): keyword stuffing lowers visibility in AI answers; Merchant Center titles stop at 150 characters",
    "clear_opening": "GEO guidance for shops: the first sentence says what the product is and who it is for",
}


def count_text(count: int, word: str) -> str:
    # 1, "listing" -> "1 listing" and 3, "listing" -> "3 listings"
    if count == 1:
        return f"{count} {word}"
    return f"{count} {word}s"


def criterion_percentages(scores: list[ProductScore]) -> dict[str, int]:
    # points earned / points possible for each criterion, as a percentage
    earned: dict[str, int] = {}
    possible: dict[str, int] = {}
    for name in CRITERIA:
        earned[name] = 0
        possible[name] = 0

    for product_score in scores:
        for result in product_score.results:
            name: str = CRITERION_OF_RULE[result.rule]
            earned[name] = earned[name] + result.points
            possible[name] = possible[name] + POINTS[result.rule]

    percentages: dict[str, int] = {}
    for name in CRITERIA:
        if possible[name] == 0:
            percentages[name] = 0
        else:
            percentages[name] = round(100 * earned[name] / possible[name])
    return percentages


def products_of(scores: list[ProductScore]) -> list:
    # the products inside the scores, in the same order
    products: list = []
    for product_score in scores:
        products.append(product_score.product)
    return products


# score grading, shared by the pdf report and the web verdict box so a score
# gets the same colour in both. separate from scoring.PASS_SCORE, which is the
# stricter per-listing cutoff for counting a single listing as "ready".
GOOD_SCORE: int = 80
MEDIUM_SCORE: int = 60


def level(score: float) -> str:
    # used to colour the scores: good (green), medium (orange), poor (red)
    if score >= GOOD_SCORE:
        return "good"
    if score >= MEDIUM_SCORE:
        return "medium"
    return "poor"


# the colours of good / medium / poor, as red, green, blue (0 to 255)
COLOUR_OF_LEVEL: dict[str, tuple[int, int, int]] = {
    "good": (31, 122, 90),
    "medium": (183, 121, 31),
    "poor": (184, 50, 50),
}
BLACK: tuple[int, int, int] = (29, 31, 30)
GREY: tuple[int, int, int] = (95, 99, 95)
LIGHT_GREY: tuple[int, int, int] = (226, 224, 216)

# the built-in pdf fonts only know the latin-1 characters (é, °, ü...), so these are swapped first
PDF_REPLACEMENTS: dict[str, str] = {"−": "-", "–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "€": "EUR", "…": "..."}


def pdf_text(text: str) -> str:
    # "−8 °C" -> "-8 °C". any other unknown character (an emoji, chinese...) becomes "?" instead of crashing
    for character, replacement in PDF_REPLACEMENTS.items():
        text = text.replace(character, replacement)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def pdf_heading(pdf: FPDF, title: str) -> None:
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*BLACK) # * unpacks the tuple: set_text_color(29, 31, 30)
    pdf.cell(0, 8, pdf_text(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)


def reset_table_colours(pdf: FPDF) -> None:
    # the score bars change the fill colour, so it is set back to white before a table
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(*LIGHT_GREY)
    pdf.set_text_color(*BLACK)


def pdf_report(scores: list[ProductScore], catalog_score: float, errors: list[str], source_name: str = "", sector: str = "") -> bytes:
    # the report is made in memory and returned as bytes, ready for the download button
    ready: int = count_ready(scores)
    percentages: dict[str, int] = criterion_percentages(scores)

    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(True, margin=15) # a new page starts by itself when the page is full
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*BLACK)
    pdf.cell(0, 12, "ShelfReady report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # file name · sector · date, skipping the empty ones
    details: list[str] = []
    for part in [source_name, sector, date.today().isoformat()]:
        if part != "":
            details.append(part)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 6, pdf_text(" · ".join(details)), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # big catalog score
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_text_color(*COLOUR_OF_LEVEL[level(catalog_score)])
    pdf.cell(0, 16, f"{catalog_score} / 100", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*BLACK)
    pdf.multi_cell(0, 6, f"AI readability score: {ready} of {len(scores)} products are likely to be recommended by a shopping assistant.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # one line per criterion: name and percentage, a coloured bar, the example
    pdf_heading(pdf, "Score breakdown")
    for name in CRITERIA:
        value: int = percentages[name]
        colour: tuple[int, int, int] = COLOUR_OF_LEVEL[level(value)]
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*BLACK)
        pdf.cell(70, 6, pdf_text(name))
        pdf.set_text_color(*colour)
        pdf.cell(15, 6, f"{value}%")
        # the bar: a grey box, then a coloured box on top as wide as the percentage
        bar_x: float = pdf.get_x()
        bar_y: float = pdf.get_y() + 2
        pdf.set_fill_color(*LIGHT_GREY)
        pdf.rect(bar_x, bar_y, 80, 2.5, style="F")
        pdf.set_fill_color(*colour)
        pdf.rect(bar_x, bar_y, 80 * value / 100, 2.5, style="F")
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*GREY)
        pdf.cell(0, 5, pdf_text(CRITERION_EXAMPLE[name]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)

    problems: list[tuple[str, int]] = most_common_problems(scores, limit=5)
    if len(problems) > 0:
        pdf_heading(pdf, "What to fix first")
        number: int = 1
        for rule, count in problems:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*BLACK)
            pdf.multi_cell(0, 6, pdf_text(f"{number}. {RULE_NAMES[rule]} · {count_text(count, 'product')}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, pdf_text(f"Fix: {HOW_TO_FIX[rule]}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*GREY)
            pdf.multi_cell(0, 4, pdf_text(BASIS_OF_RULE[rule]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)
            number = number + 1

    # shopper questions: which listings an assistant can show for each question
    summary: list[dict] = question_summary(products_of(scores))
    if len(summary) > 0:
        pdf_heading(pdf, "Shopper questions")
        pdf.set_text_color(*GREY)
        pdf.multi_cell(0, 5, "Typical requests made to an AI assistant. A product without the spec the assistant needs cannot be matched, even if it fits.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)
        reset_table_colours(pdf)
        pdf.set_font("Helvetica", "", 9)
        with pdf.table(col_widths=(50, 25, 25), text_align="LEFT") as table:
            table.row(["Shopper asks for", "Shown", "Cannot be matched"])
            for entry in summary:
                table.row([pdf_text(entry["question"]), pdf_text(", ".join(entry["matches"])), pdf_text(", ".join(entry["unknown"]))])

    # one table row per product
    pdf_heading(pdf, "Products")
    reset_table_colours(pdf)
    pdf.set_font("Helvetica", "", 9)
    with pdf.table(col_widths=(10, 30, 9, 11, 50), text_align="LEFT") as table:
        table.row(["ID", "Product", "Score", "Status", "To fix"])
        for product_score in scores:
            status: str = "To fix"
            if product_score.is_ready:
                status = "Ready"
            elif product_score.blocked:
                status = "Blocked"

            fixes: list[str] = []
            for result in product_score.failed:
                fixes.append(f"{RULE_NAMES[result.rule]}: {result.message}")
            for question in unanswered_questions(product_score.product):
                fixes.append(f"Cannot be matched to: {question}")

            table.row([
                pdf_text(product_score.product.id),
                pdf_text(product_score.product.title),
                str(product_score.score),
                status,
                pdf_text("\n".join(fixes)),
            ])

    if len(errors) > 0:
        pdf_heading(pdf, "Rows skipped")
        for error in errors:
            pdf.multi_cell(0, 5, pdf_text(f"- {error}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
