"""ShelfReady web page. Run from the python/ folder:
    conda activate nomades_nppd_312
    streamlit run shelfready_app.py
The checks are the same as the command line, this file only shows the results."""

import json
from pathlib import Path

import streamlit as st

from shelfready.loader import LoaderError, decode_bytes, load_products_from_text
from shelfready.models import Product
from shelfready.questions import question_summary, unanswered_questions
from shelfready.report import (
    Basis_of_rule,
    Criteria,
    How_to_fix,
    Rule_names,
    criterion_percentages,
    html_report,
    json_report,
)
from shelfready.scoring import Pass_score, ProductScore, count_ready, count_unanswered, most_common_problems, score_catalog
from shelfready.sector import Expected_attributes, Sector

Sample_file: Path = Path(__file__).parent / "shelfready" / "data" / "sample_products.csv"

# a small file the shop owner can download and fill in
Template_csv: str = (
    "id,category,title,description,price,currency,availability,gtin,brand,image_url,attributes\n"
    "P001,backpack,Trail daypack 30 l,Hiking daypack with a rain cover. Holds 30 l and weighs 900 g.,"
    "89.00,EUR,in_stock,4006381333931,Nordwear,https://example.com/p001.jpg,volume_l: 30 | weight_g: 900 | material: nylon\n"
)

# tooltips for the criteria
Criterion_help: dict[str, str] = {
    "Distinctive attributes": "Can an assistant tell your product apart from others of the same type?",
    "Disambiguation": "Is there anything an assistant cannot understand: numbers without units, vague claims, a wrong barcode?",
    "Price / content coherence": "Does the listing contradict itself, or give values that look wrong?",
    "Structuring": "Are the specs in the attributes column, or hidden in the description text?",
}


def status_of(product_score: ProductScore) -> str:
    if product_score.is_ready:
        return "✅ Ready"
    if product_score.blocked:
        return "⛔ Blocked"
    return "🔧 To fix"


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
            "3. Fix the listings marked 🔧 or ⛔, starting with the lowest score.\n"
            "4. Upload again and watch the score go up."
        )
        st.header("Your file")
        st.markdown(
            "Needed columns: **id**, **title**, **price**.  \n"
            "Also read: category, description, currency, availability, gtin, brand, image_url, attributes.  \n"
            "Write the specs in **attributes** like this: `volume_l: 30 | weight_g: 900`"
        )
        st.download_button("Download a template", Template_csv, file_name="shelfready_template.csv", mime="text/csv")
        st.header("Categories checked")
        st.caption(", ".join(Expected_attributes.keys()) + ". Other categories get a basic check.")


def show_welcome() -> None:
    st.info("Upload a CSV file, or tick the sample shop, to start.")
    st.markdown(
        "ShelfReady reads your product list and tells you, listing by listing, "
        "what stops an AI shopping assistant from understanding and recommending it, "
        "and how to fix it."
    )


def show_verdict(scores: list[ProductScore], catalog_score: float) -> None:
    # green, orange or red box
    ready: int = count_ready(scores)
    to_fix: int = len(scores) - ready

    message: str = f"**{catalog_score} / 100**: {ready} of {len(scores)} listings are ready, {to_fix} need work."
    if catalog_score >= Pass_score:
        st.success(message)
    elif catalog_score >= 70:
        st.warning(message)
    else:
        st.error(message)


def show_overview(scores: list[ProductScore], catalog_score: float) -> None:
    left, middle, right = st.columns(3)
    left.metric("AI readability score", f"{catalog_score} / 100", help=f"A listing counts as ready from {Pass_score} points.")
    middle.metric("Ready listings", f"{count_ready(scores)} of {len(scores)}")
    right.metric("Shopper questions not matched", count_unanswered(scores), help="See the Shopper questions tab.")

    st.subheader("Score by criterion")
    percentages: dict[str, int] = criterion_percentages(scores)
    columns = st.columns(len(Criteria))
    for index in range(len(Criteria)):
        name: str = Criteria[index]
        columns[index].metric(name, f"{percentages[name]}%", help=Criterion_help[name])
        columns[index].progress(percentages[name] / 100) # needs a value from 0 to 1

    problems: list[tuple[str, int]] = most_common_problems(scores, limit=3)
    if len(problems) > 0:
        st.subheader("Fix these first")
        for rule, count in problems:
            st.markdown(f"**{Rule_names[rule]}** ({count} listing(s))  \n{How_to_fix[rule]}")


def show_listings(scores: list[ProductScore]) -> None:
    only_to_fix: bool = st.toggle("Show only listings that need work", value=True)

    # worst first
    sorted_scores: list[ProductScore] = sorted(scores, key=score_of)

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
    st.dataframe(rows, hide_index=True, width="stretch")

    st.subheader("What to change, listing by listing")
    for product_score in sorted_scores:
        if not needs_work(product_score):
            continue
        title: str = product_score.product.title
        if title == "":
            title = "(no title)"
        with st.expander(f"{status_of(product_score)}  {product_score.product.id}  {title}  ({product_score.score} / 100)"):
            if product_score.blocked:
                st.error("Google Shopping would reject this listing as it is. Fix this first.")
            for result in product_score.failed:
                st.markdown(f"**{Rule_names[result.rule]}**: {result.message}  \nFix: {How_to_fix[result.rule]}")
                st.caption(Basis_of_rule[result.rule])
            for question in unanswered_questions(product_score.product):
                st.markdown(f"**Cannot be matched**: {question}")


def show_questions(products: list[Product]) -> None:
    summary: list[dict] = question_summary(products)
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
    st.dataframe(rows, hide_index=True, width="stretch")


def show_downloads(scores: list[ProductScore], catalog_score: float, errors: list[str], source_name: str) -> None:
    st.markdown("Keep a copy of the results, or send the report to a colleague.")
    page: str = html_report(scores, catalog_score, errors, source_name, Sector)
    data: dict = json_report(scores, catalog_score, errors, source_name, Sector)
    left, right = st.columns(2)
    left.download_button("Report (HTML)", page, file_name="shelfready_report.html", mime="text/html")
    right.download_button("Results (JSON)", json.dumps(data, indent=2, ensure_ascii=False), file_name="shelfready_results.json", mime="application/json")

    if len(errors) > 0:
        st.subheader("Rows that could not be read")
        for error in errors:
            st.warning(error)


def main() -> None:
    st.set_page_config(page_title="ShelfReady", page_icon="🛒", layout="wide")
    show_sidebar()
    st.title("ShelfReady")
    st.write("Will an AI shopping assistant understand and recommend your products?")
    st.caption(f"Sector: {Sector}. Your file stays on this computer.")

    uploaded = st.file_uploader("Upload your product CSV", type=["csv"])
    use_sample: bool = st.checkbox("Try the sample outdoor shop instead")

    # the uploaded file first, otherwise the sample
    try:
        if uploaded is not None:
            source_name: str = uploaded.name
            text: str = decode_bytes(uploaded.getvalue(), source_name)
        elif use_sample:
            source_name = Sample_file.name
            text = decode_bytes(Sample_file.read_bytes(), source_name)
        else:
            show_welcome()
            return
        products: list[Product]
        errors: list[str]
        products, errors = load_products_from_text(text)
    except LoaderError as error:
        st.error(f"This file cannot be read. {error}")
        return

    if len(products) == 0:
        st.warning("No product could be read from this file. Check that it has the columns id, title and price.")
        return

    scores: list[ProductScore]
    catalog_score: float
    scores, catalog_score = score_catalog(products)

    show_verdict(scores, catalog_score)
    overview, listings, questions, downloads = st.tabs(["Overview", "Listings", "Shopper questions", "Download"])
    with overview:
        show_overview(scores, catalog_score)
    with listings:
        show_listings(scores)
    with questions:
        show_questions(products)
    with downloads:
        show_downloads(scores, catalog_score, errors, source_name)


if __name__ == "__main__":
    main()
