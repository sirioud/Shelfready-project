# ShelfReady web page (streamlit), the only entry point of the app.
# Run locally with: streamlit run shelfready_app.py
# Streamlit runs this whole file again from top to bottom on every click,
# so nothing is kept between two clicks unless the widget itself remembers it (the uploaded file, the checkbox).
# This file only shows things: the loading, scoring and reports are in the shelfready/ package.

from pathlib import Path

import pandas as pd # comes with streamlit, used to colour the table cells
import streamlit as st

from shelfready.ai_search import BENEFIT_UNCLEAR, AISearchError, load_api_key, load_recorded, run_search
from shelfready.feed import supplemental_feed
from shelfready.loader import LoaderError, decode_bytes, load_products_from_text
from shelfready.models import Product
from shelfready.questions import NO, UNKNOWN, YES, question_summary, unanswered_questions
from shelfready.report import (
    BASIS_OF_RULE,
    CRITERIA,
    CRITERION_EXAMPLE,
    HOW_TO_FIX,
    RULE_NAMES,
    count_text,
    criterion_percentages,
    level,
    pdf_report,
)
from shelfready.scoring import PASS_SCORE, ProductScore, count_ready, count_unanswered, most_common_problems, score_catalog
from shelfready.sector import EXPECTED_ATTRIBUTES, SECTOR

# __file__ = the path of this file, so the sample is found whatever folder the app is started from
SAMPLE_FILE: Path = Path(__file__).parent / "shelfready" / "data" / "sample_products.csv"
# the recorded Gemini answers for the sample shop, so the demo works without a key or a network
AI_SAMPLE_FILE: Path = Path(__file__).parent / "shelfready" / "data" / "ai_search_sample.json"
# what the specs say about a need, in plain words for the AI search table
SPECS_FIT_LABEL: dict[str, str] = {YES: "Yes", NO: "No", UNKNOWN: "Spec missing"}


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

# cell colours, same green / orange / red as the pdf report
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
    # everything written inside "with st.sidebar:" goes in the left column instead of the main page
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
            "Needed columns: id, title, price.  \n"
            "Also read: category, description, currency, availability, barcode (GTIN), brand, image URL, attributes.  \n"
            "Write the specs (volume, weight, material...) in the attributes column. "
            "Download the template below to see the exact column names and format."
        )
        st.download_button("Download a template", TEMPLATE_CSV, file_name="shelfready_template.csv", mime="text/csv")
        st.header("Categories checked")
        categories: list[str] = []
        for category in EXPECTED_ATTRIBUTES.keys():
            categories.append(category.replace("_", " ")) # "sleeping_bag" -> "sleeping bag"
        st.caption(", ".join(categories) + ". Other categories get a basic check.")


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
    # same green / orange / red grading as the pdf report
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
    # border=True draws each number as a card
    left.metric("AI readability score", f"{result.catalog_score} / 100", help=f"A listing counts as ready from {PASS_SCORE} points.", border=True)
    middle.metric("Ready listings", f"{count_ready(scores)} of {len(scores)}", border=True)
    right.metric("Shopper questions not matched", count_unanswered(scores), help="See the Shopper questions tab.", border=True)

    st.subheader("Score breakdown")
    percentages: dict[str, int] = criterion_percentages(scores)
    # one column per criterion: zip pairs the first criterion with the first column, the second with the second...
    for name, column in zip(CRITERIA, st.columns(len(CRITERIA))):
        with column.container(border=True): # one card per criterion
            st.metric(name, f"{percentages[name]}%", help=CRITERION_HELP[name])
            st.progress(percentages[name] / 100) # needs a value from 0 to 1
            st.caption(CRITERION_EXAMPLE[name])

    problems: list[tuple[str, int]] = most_common_problems(scores, limit=3)
    if len(problems) > 0:
        st.subheader("Fix these first")
        for rule, count in problems:
            with st.container(border=True):
                st.markdown(f"**{RULE_NAMES[rule]}** · {count_text(count, 'listing')}  \n{HOW_TO_FIX[rule]}")


def show_listings(result: AuditResult) -> None:
    only_to_fix: bool = st.toggle("Show only listings that need work", value=True)

    # worst first: sorted() calls score_of on each listing and sorts by that number, smallest first
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
    # .style.map calls status_cell on every cell of the Status column and uses the css it returns
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
        "Each line is something a shopper could ask an AI assistant, for example ChatGPT or Gemini. "
        "\"Shown\" lists your products the assistant can suggest for that request. "
        "\"Cannot be matched\" lists products the assistant has to skip, because the spec it needs "
        "is missing from your file. Even a product that fits the request perfectly is never suggested. "
        "Add that spec to the attributes column and the product can be shown."
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


def show_ai_search(result: AuditResult) -> None:
    st.markdown(
        "A shopper describes a need to an AI assistant, for example \"a headlamp for night trail running\". "
        "The AI picks the products it would recommend, and ShelfReady compares its picks with what your specs prove. "
        "\"Benefit unclear\" means the product fits, but the AI did not see it: say what it is for and for whom."
    )
    st.caption("This sends your listings to Google's Gemini API. Results can vary between runs. The score above does not use it.")

    api_key: str = load_api_key()
    pressed: bool = st.button("Run with live AI", disabled=api_key == "")
    if api_key == "":
        st.caption("No Gemini key: set GEMINI_API_KEY or config/gemini_creds.json to run the live test.")

    try:
        if pressed:
            with st.spinner("Asking Gemini..."):
                rows: list[dict] = run_search(result.products, api_key)
        elif result.source_name == SAMPLE_FILE.name:
            recorded: dict = load_recorded(AI_SAMPLE_FILE)
            st.caption(f"Recorded run, {recorded['recorded_on']} ({recorded['model']})")
            rows = run_search(result.products, "", recorded=recorded)
        else:
            return # an uploaded file: nothing is sent until the button is pressed
    except AISearchError as error:
        st.error(str(error))
        return

    if len(rows) == 0:
        st.info("No shopper needs for the categories in this file.")
        return

    # how many listings fit by their specs, and how many of those the AI did not pick
    fitting: int = 0
    unclear: int = 0
    for row in rows:
        if row["fits"] == YES:
            fitting = fitting + 1
        if row["verdict"] == BENEFIT_UNCLEAR:
            unclear = unclear + 1
    st.metric("Benefit unclear", f"{unclear} of {fitting} listings", help="Listings that fit the need by their specs, but that the AI did not recommend.")

    table: list[dict] = []
    for row in rows:
        recommends: str = "No"
        if row["recommended"]:
            recommends = "Yes"
        table.append({
            "Shopper need": row["need"],
            "Listing": row["id"],
            "Specs fit": SPECS_FIT_LABEL[row["fits"]],
            "AI recommends": recommends,
            "AI's reason": row["reason"],
            "Verdict": row["verdict"].capitalize(),
        })
    st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")


def show_downloads(result: AuditResult) -> None:
    st.markdown("Keep a copy of the results, or send the report to a colleague.")
    report: bytes = pdf_report(result.scores, result.catalog_score, result.errors, result.source_name, SECTOR)
    # the file is made in memory and handed to the browser, nothing is written on the server
    st.download_button("Report (PDF)", report, file_name="shelfready_report.pdf", mime="application/pdf")

    st.subheader("AI-ready feed")
    st.markdown(
        "A supplemental feed for Google Merchant Center, made from your own specs. "
        "It adds product highlights and questions and answers, two attributes that "
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
        # types declared first, because the function returns two values at once (a tuple)
        products: list[Product]
        errors: list[str]
        products, errors = load_products_from_text(text)
    except LoaderError as error:
        # the whole file is unusable: show the reason from loader.py instead of crashing the page
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
    st.set_page_config(page_title="ShelfReady", page_icon=":material/landscape:", layout="wide")
    show_sidebar()
    st.title(":material/landscape: ShelfReady")
    st.write("Will an AI shopping assistant understand and recommend your products?")
    st.caption(f"Sector: {SECTOR}. Your file is only read to score it, never saved.")

    result: AuditResult | None = load_input()
    if result is None:
        return # nothing to score yet, load_input already showed a message

    show_verdict(result)
    overview, listings, questions, ai_search, downloads = st.tabs([
        ":material/dashboard: Overview",
        ":material/list_alt: Listings",
        ":material/help: Shopper questions",
        ":material/smart_toy: AI search test",
        ":material/download: Download",
    ])
    with overview:
        show_overview(result)
    with listings:
        show_listings(result)
    with questions:
        show_questions(result)
    with ai_search:
        show_ai_search(result)
    with downloads:
        show_downloads(result)


# streamlit run (and the AppTest in the tests) runs this file as "__main__", so the page is drawn
# importing it from another file does not draw anything
if __name__ == "__main__":
    main()
