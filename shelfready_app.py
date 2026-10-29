import json
from pathlib import Path

import pandas as pd # comes with streamlit, used to colour the table cells
import streamlit as st

from shelfready.feed import supplemental_feed
from shelfready.loader import LoaderError, decode_bytes, load_products_from_text
from shelfready.models import Product
from shelfready.questions import question_summary, unanswered_questions
from shelfready.report import (
    BASIS_OF_RULE,
    CRITERIA,
    HOW_TO_FIX,
    RULE_NAMES,
    criterion_percentages,
    html_report,
    json_report,
    level,
)
from shelfready.scoring import PASS_SCORE, ProductScore, count_ready, count_unanswered, most_common_problems, score_catalog
from shelfready.sector import EXPECTED_ATTRIBUTES, SECTOR

SAMPLE_FILE: Path = Path(__file__).parent / "shelfready" / "data" / "sample_products.csv"


class AuditResult:
    # everything one audit produces, bundled so it travels as a single value
    def __init__(
        self,
        products: list[Product],
        scores: list[ProductScore],
        catalog_score: float,
        errors: list[str],
        source_name: str,
    ):
        self.products: list[Product] = products
        self.scores: list[ProductScore] = scores
        self.catalog_score: float = catalog_score
        self.errors: list[str] = errors
        self.source_name: str = source_name

# a small file the shop owner can download and fill in
TEMPLATE_CSV: str = (
    "id,category,title,description,price,currency,availability,gtin,brand,image_url,attributes\n"
    "P001,backpack,Trail daypack 30 l,Hiking daypack with a rain cover. Holds 30 l and weighs 900 g.,"
    "89.00,EUR,in_stock,4006381333931,Nordwear,https://example.com/p001.jpg,volume_l: 30 | weight_g: 900 | material: nylon\n"
)

# tooltips for the criteria
CRITERION_HELP: dict[str, str] = {
    "Distinctive attributes": "Can an assistant tell your product apart from others of the same type?",
    "Disambiguation": "Is there anything an assistant cannot understand: numbers without units, vague claims, a wrong barcode?",
    "Price / content coherence": "Does the listing contradict itself, or give values that look wrong?",
    "Structuring": "Are the specs in the attributes column, or hidden in the description text?",
    "Clear wording": "Is the text written for an AI assistant: facts instead of marketing words, a clear first sentence, no keyword stuffing?",
}

# cell colours, same green / orange / red as the html report
# a light background with dark text, so it stays readable in light and dark mode
GOOD_CELL: str = "background-color: #d9efe6; color: #1f7a5a"
MEDIUM_CELL: str = "background-color: #f8ead2; color: #8a5a12"
POOR_CELL: str = "background-color: #f6dada; color: #b83232"

STATUS_CELL: dict[str, str] = {"Ready": GOOD_CELL, "To fix": MEDIUM_CELL, "Blocked": POOR_CELL}
# streamlit colour names for the status in the expander titles and badges
STATUS_COLOUR: dict[str, str] = {"Ready": "green", "To fix": "orange", "Blocked": "red"}


def status_of(product_score: ProductScore) -> str:
    if product_score.is_ready:
        return "Ready"
    if product_score.blocked:
        return "Blocked"
    return "To fix"


def status_cell(status: str) -> str:
    # css for one cell of the Status column
    if status in STATUS_CELL:
        return STATUS_CELL[status]
    return ""


def missing_cell(listings: str) -> str:
    # css for the "Cannot be matched" column: red only when some listings are missing
    if listings == "":
        return ""
    return POOR_CELL


def score_of(product_score: ProductScore) -> int:
    # used by sorted() to sort the listings by score
    return product_score.score


def needs_work(product_score: ProductScore) -> bool:
    # a ready listing can still have small problems, those are shown too
    return not product_score.is_ready or len(product_score.failed) > 0


def show_sidebar() -> None:
    with st.sidebar:
        st.header("How it works")
        st.markdown(
            "1. Export your products as a CSV file.\n"
            "2. Upload it here.\n"
            "3. Fix the listings marked To fix or Blocked, starting with the lowest score.\n"
            "4. Upload again and watch the score go up."
        )
        st.header("Your file")
        st.markdown(
            "Needed columns: **id**, **title**, **price**.  \n"
            "Also read: category, description, currency, availability, gtin, brand, image_url, attributes.  \n"
            "Write the specs in **attributes** like this: `volume_l: 30 | weight_g: 900`"
        )
        st.download_button("Download a template", TEMPLATE_CSV, file_name="shelfready_template.csv", mime="text/csv")
        st.header("Categories checked")
        st.caption(", ".join(EXPECTED_ATTRIBUTES.keys()) + ". Other categories get a basic check.")


def show_welcome() -> None:
    st.info("Upload a CSV file, or tick the sample shop, to start.")
    st.markdown(
        "ShelfReady reads your product list and tells you, listing by listing, "
        "what stops an AI shopping assistant from understanding and recommending it, "
        "and how to fix it."
    )


def show_verdict(result: AuditResult) -> None:
    scores: list[ProductScore] = result.scores
    ready: int = count_ready(scores)
    to_fix: int = len(scores) - ready

    message: str = f"**{result.catalog_score} / 100**: {ready} of {len(scores)} listings are ready, {to_fix} need work."
    # same green / orange / red grading as the html report
    grade: str = level(result.catalog_score)
    if grade == "good":
        st.success(message)
    elif grade == "medium":
        st.warning(message)
    else:
        st.error(message)


def show_overview(result: AuditResult) -> None:
    scores: list[ProductScore] = result.scores
    left, middle, right = st.columns(3)
    left.metric("AI readability score", f"{result.catalog_score} / 100", help=f"A listing counts as ready from {PASS_SCORE} points.")
    middle.metric("Ready listings", f"{count_ready(scores)} of {len(scores)}")
    right.metric("Shopper questions not matched", count_unanswered(scores), help="See the Shopper questions tab.")

    st.subheader("Score by criterion")
    percentages: dict[str, int] = criterion_percentages(scores)
    for name, column in zip(CRITERIA, st.columns(len(CRITERIA))):
        column.metric(name, f"{percentages[name]}%", help=CRITERION_HELP[name])
        column.progress(percentages[name] / 100) # needs a value from 0 to 1

    problems: list[tuple[str, int]] = most_common_problems(scores, limit=3)
    if len(problems) > 0:
        st.subheader("Fix these first")
        for rule, count in problems:
            st.markdown(f"**{RULE_NAMES[rule]}** ({count} listing(s))  \n{HOW_TO_FIX[rule]}")


def show_listings(result: AuditResult) -> None:
    only_to_fix: bool = st.toggle("Show only listings that need work", value=True)

    # worst first
    sorted_scores: list[ProductScore] = sorted(result.scores, key=score_of)

    rows: list[dict] = []
    for product_score in sorted_scores:
        if only_to_fix and not needs_work(product_score):
            continue
        rows.append({
            "ID": product_score.product.id,
            "Product": product_score.product.title,
            "Score": product_score.score,
            "Status": status_of(product_score),
            "Problems": len(product_score.failed),
        })
    if len(rows) == 0:
        st.success("Every listing is ready. Nothing to fix.")
        return
    # the status carries the colour, the score is shown as a bar out of 100
    table = pd.DataFrame(rows).style.map(status_cell, subset=["Status"])
    score_bar = st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d")
    st.dataframe(table, hide_index=True, width="stretch", column_config={"Score": score_bar})

    st.subheader("What to change, listing by listing")
    for product_score in sorted_scores:
        if not needs_work(product_score):
            continue
        title: str = product_score.product.title
        if title == "":
            title = "(no title)"
        status: str = status_of(product_score)
        colour: str = STATUS_COLOUR[status]
        # :colour[text] is streamlit markdown for coloured text
        with st.expander(f":{colour}[**{status}**] · {product_score.product.id}  {title}  ({product_score.score} / 100)"):
            st.badge(f"{status} · {product_score.score} / 100", color=colour)
            if product_score.blocked:
                st.error("Google Shopping would reject this listing as it is. Fix this first.")
            # rule_result, not result: result is already the AuditResult this function receives
            for rule_result in product_score.failed:
                st.markdown(f"**{RULE_NAMES[rule_result.rule]}**: {rule_result.message}  \nFix: {HOW_TO_FIX[rule_result.rule]}")
                st.caption(BASIS_OF_RULE[rule_result.rule])
            for question in unanswered_questions(product_score.product):
                st.markdown(f"**Cannot be matched**: {question}")


def show_questions(result: AuditResult) -> None:
    summary: list[dict] = question_summary(result.products)
    if len(summary) == 0:
        st.info("No shopper questions for the categories in this file.")
        return
    st.markdown(
        "These are typical requests made to an AI assistant. "
        "A listing **cannot be matched** when the spec the assistant needs is missing: "
        "the product may fit perfectly, but it will never be shown."
    )
    rows: list[dict] = []
    for entry in summary:
        rows.append({
            "Shopper asks for": entry["question"],
            "Shown": ", ".join(entry["matches"]),
            "Cannot be matched": ", ".join(entry["unknown"]),
        })
    table = pd.DataFrame(rows).style.map(missing_cell, subset=["Cannot be matched"])
    st.dataframe(table, hide_index=True, width="stretch")


def show_downloads(result: AuditResult) -> None:
    st.markdown("Keep a copy of the results, or send the report to a colleague.")
    page: str = html_report(result.scores, result.catalog_score, result.errors, result.source_name, SECTOR)
    data: dict = json_report(result.scores, result.catalog_score, result.errors, result.source_name, SECTOR)
    left, right = st.columns(2)
    left.download_button("Report (HTML)", page, file_name="shelfready_report.html", mime="text/html")
    right.download_button("Results (JSON)", json.dumps(data, indent=2, ensure_ascii=False), file_name="shelfready_results.json", mime="application/json")

    st.subheader("AI-ready feed")
    st.markdown(
        "A supplemental feed for Google Merchant Center, made from your own specs. "
        "It adds **product highlights** and **questions and answers**, two attributes that "
        "Google AI Mode and Gemini read. Check it, then add it in Merchant Center as a supplemental data source. "
        "Listings whose specs disagree with the title or look wrong are left out until they are fixed."
    )
    st.download_button("AI-ready feed (TSV)", supplemental_feed(result.products), file_name="shelfready_ai_feed.tsv", mime="text/tab-separated-values")

    if len(result.errors) > 0:
        st.subheader("Rows that could not be read")
        for error in result.errors:
            st.warning(error)


def load_input() -> AuditResult | None:
    # reads the uploaded file (or the sample), or shows the welcome and returns None when there is nothing to score
    uploaded = st.file_uploader("Upload your product CSV", type=["csv"])
    use_sample: bool = st.checkbox("Try the sample outdoor shop instead")

    # the uploaded file first, otherwise the sample
    try:
        if uploaded is not None:
            source_name: str = uploaded.name
            text: str = decode_bytes(uploaded.getvalue(), source_name)
        elif use_sample:
            source_name = SAMPLE_FILE.name
            text = decode_bytes(SAMPLE_FILE.read_bytes(), source_name)
        else:
            show_welcome()
            return None
        products: list[Product]
        errors: list[str]
        products, errors = load_products_from_text(text)
    except LoaderError as error:
        st.error(f"This file cannot be read. {error}")
        return None

    if len(products) == 0:
        st.warning("No product could be read from this file. Check that it has the columns id, title and price.")
        return None

    scores: list[ProductScore]
    catalog_score: float
    scores, catalog_score = score_catalog(products)
    return AuditResult(products, scores, catalog_score, errors, source_name)


def main() -> None:
    st.set_page_config(page_title="ShelfReady", layout="wide")
    show_sidebar()
    st.title("ShelfReady")
    st.write("Will an AI shopping assistant understand and recommend your products?")
    st.caption(f"Sector: {SECTOR}. Your file is only read to score it, never saved.")

    result: AuditResult | None = load_input()
    if result is None:
        return

    show_verdict(result)
    overview, listings, questions, downloads = st.tabs(["Overview", "Listings", "Shopper questions", "Download"])
    with overview:
        show_overview(result)
    with listings:
        show_listings(result)
    with questions:
        show_questions(result)
    with downloads:
        show_downloads(result)


if __name__ == "__main__":
    main()
