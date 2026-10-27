# The two reports the web page offers for download: an html page and the json results.

from datetime import date
from html import escape

from .rules import POINTS, CRITERION_OF_RULE
from .questions import question_summary, unanswered_questions
from .scoring import ProductScore, count_ready, most_common_problems

# the five criteria, in display order. each rule is mapped to one of these in rules.RULE_REGISTRY
CRITERIA: list[str] = ["Distinctive attributes", "Disambiguation", "Price / content coherence", "Structuring", "Clear wording"]

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
    "expected_attributes": "Add the missing specs to the attributes column, e.g. limit_c: -8 for a sleeping bag.",
    "attribute_count": "Give at least 3 specs in the attributes column (weight, size, material...).",
    "units": "Write the unit after every number: 75 kg, not 75.",
    "compatibility": "Name the exact models it works with instead of 'most' or 'all'.",
    "quantity": "Add pack_size: 2 (or the right number) to the attributes.",
    "gtin": "Copy the barcode from the box. The last digit is a check digit, so one typo makes it invalid.",
    "feed_standard": "Fill in the title and price and image_url, use in_stock / out_of_stock / preorder / backorder, and give a real brand.",
    "price_coherence": "Write a longer description: an expensive product needs at least 120 characters.",
    "spec_agreement": "Make the title, the description and the attributes say the same number.",
    "plausible_values": "Check the value and its unit: weight_g is in grams, temperatures go comfort > limit > extreme.",
    "structured_share": "Copy the numbers from the description into the attributes column, e.g. lumens_lm: 400.",
    "facts_not_claims": "Replace each claim with a number: 'ultra-light' becomes 'weighs 780 g'.",
    "keyword_stuffing": "Write the title as a name, each word once: brand, product type, key spec.",
    "clear_opening": "Start the description with what the product is and what it is for: 'Hiking daypack for day trips...'.",
}

# why each rule exists, shown in the html report
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


# score grading, shared by the html report and the web verdict box so a score
# gets the same colour in both. separate from scoring.PASS_SCORE, which is the
# stricter per-listing cutoff for counting a single listing as "ready".
GOOD_SCORE: int = 80
MEDIUM_SCORE: int = 60


def level(score: float) -> str:
    # used as a css class to colour the scores: good (green), medium (orange), poor (red)
    if score >= GOOD_SCORE:
        return "good"
    if score >= MEDIUM_SCORE:
        return "medium"
    return "poor"


STYLE: str = """
:root { --ink:#1d1f1e; --muted:#5f635f; --line:#e2e0d8; --bg:#f7f6f2; --card:#fff;
        --good:#1f7a5a; --medium:#b7791f; --poor:#b83232; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
       font-family:-apple-system, "Segoe UI", Helvetica, Arial, sans-serif; line-height:1.5; }
main { max-width:960px; margin:0 auto; padding:48px 24px 80px; }
h1 { font-size:2rem; margin:0 0 4px; } h2 { font-size:1.15rem; margin:40px 0 12px; }
.sub { color:var(--muted); margin:0 0 32px; }
.hero { display:flex; gap:24px; align-items:center; flex-wrap:wrap; }
.big { font-size:4.5rem; font-weight:700; line-height:1; }
.big small { font-size:1.2rem; color:var(--muted); font-weight:400; }
.card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:20px; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; }
.bar { height:8px; background:var(--line); border-radius:4px; overflow:hidden; margin-top:8px; }
.bar span { display:block; height:100%; }
.good { color:var(--good); } .medium { color:var(--medium); } .poor { color:var(--poor); }
.bar .good { background:var(--good); } .bar .medium { background:var(--medium); } .bar .poor { background:var(--poor); }
table { width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line); }
th, td { text-align:left; padding:12px 14px; border-bottom:1px solid var(--line); vertical-align:top; }
th { font-size:.8rem; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
.score { font-weight:700; white-space:nowrap; }
.fix { margin:0; padding-left:18px; color:var(--muted); font-size:.92rem; }
.basis { color:var(--muted); font-size:.85rem; }
.tag { display:inline-block; font-size:.75rem; padding:2px 8px; border-radius:999px; border:1px solid var(--line); }
.tag.ready { color:var(--good); border-color:var(--good); } .tag.fix { color:var(--poor); border-color:var(--poor); }
.wide { overflow-x:auto; }
"""


def html_report(scores: list[ProductScore], catalog_score: float, errors: list[str], source_name: str = "", sector: str = "") -> str:
    # escape() is used on all product text so a title like "<script>" cannot break the page
    ready: int = count_ready(scores)
    percentages: dict[str, int] = criterion_percentages(scores)

    page: list[str] = []
    page.append("<!DOCTYPE html>")
    page.append('<html lang="en"><head><meta charset="utf-8">')
    page.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    page.append("<title>ShelfReady report</title>")
    page.append(f"<style>{STYLE}</style></head><body><main>")
    page.append("<h1>ShelfReady report</h1>")

    # file name · sector · date, skipping the empty ones
    details: list[str] = []
    for part in [escape(source_name), escape(sector), date.today().isoformat()]:
        if part != "":
            details.append(part)
    page.append(f'<p class="sub">{" · ".join(details)}</p>')

    # big catalog score
    page.append('<div class="hero">')
    page.append(f'<div class="big {level(catalog_score)}">{catalog_score}<small> / 100</small></div>')
    page.append(f"<div><strong>AI readability score</strong><br>{ready} of {len(scores)} products are likely to be recommended by a shopping assistant.</div>")
    page.append("</div>")

    # one card per criterion
    page.append("<h2>Score by criterion</h2>")
    page.append('<div class="grid">')
    for name in CRITERIA:
        value: int = percentages[name]
        page.append(
            f'<div class="card"><strong>{escape(name)}</strong>'
            f'<div class="{level(value)}" style="font-size:1.6rem;font-weight:700">{value}%</div>'
            f'<div class="bar"><span class="{level(value)}" style="width:{value}%"></span></div></div>'
        )
    page.append("</div>")

    problems: list[tuple[str, int]] = most_common_problems(scores, limit=5)
    if len(problems) > 0:
        page.append("<h2>What to fix first</h2>")
        page.append('<div class="card"><ol class="fix" style="color:var(--ink)">')
        for rule, count in problems:
            page.append(
                f"<li><strong>{escape(RULE_NAMES[rule])}</strong> ({escape(CRITERION_OF_RULE[rule])}): {count} product(s)<br>"
                f"Fix: {escape(HOW_TO_FIX[rule])}<br>"
                f'<span class="basis">{escape(BASIS_OF_RULE[rule])}</span></li>'
            )
        page.append("</ol></div>")

    # shopper questions: which listings an assistant can show for each question
    summary: list[dict] = question_summary(products_of(scores))
    if len(summary) > 0:
        page.append("<h2>Shopper questions</h2>")
        page.append('<p class="sub">Typical questions asked to an AI assistant. A listing without the needed attribute cannot be matched, even if the product fits.</p>')
        page.append('<div class="wide"><table><tr><th>Question</th><th>Matches</th><th>Cannot be matched</th></tr>')
        for entry in summary:
            matches: str = escape(", ".join(entry["matches"]))
            unknown: str = escape(", ".join(entry["unknown"]))
            page.append(f'<tr><td>{escape(entry["question"])}</td><td class="good">{matches}</td><td class="poor">{unknown}</td></tr>')
        page.append("</table></div>")

    # one table row per product
    page.append("<h2>Products</h2>")
    page.append('<div class="wide"><table><tr><th>ID</th><th>Product</th><th>Score</th><th>Status</th><th>To fix</th></tr>')
    for product_score in scores:
        status: str = "fix"
        label: str = "To fix"
        if product_score.is_ready:
            status = "ready"
            label = "Ready"
        elif product_score.blocked:
            label = "Blocked"

        fixes: str = ""
        for result in product_score.failed:
            fixes = fixes + f"<li><strong>{escape(RULE_NAMES[result.rule])}</strong>: {escape(result.message)}</li>"
        for question in unanswered_questions(product_score.product):
            fixes = fixes + f"<li>Cannot be matched to: {escape(question)}</li>"
        if fixes != "":
            fixes = f'<ul class="fix">{fixes}</ul>'

        page.append(
            f"<tr><td>{escape(product_score.product.id)}</td><td>{escape(product_score.product.title)}</td>"
            f'<td class="score {level(product_score.score)}">{product_score.score}</td>'
            f'<td><span class="tag {status}">{label}</span></td><td>{fixes}</td></tr>'
        )
    page.append("</table></div>")

    if len(errors) > 0:
        page.append("<h2>Rows skipped</h2>")
        page.append('<div class="card"><ul class="fix">')
        for error in errors:
            page.append(f"<li>{escape(error)}</li>")
        page.append("</ul></div>")

    page.append("</main></body></html>")
    return "\n".join(page)


def json_report(scores: list[ProductScore], catalog_score: float, errors: list[str], source_name: str = "", sector: str = "") -> dict:
    # plain values only, so json.dumps can save it
    products: list[dict] = []
    for product_score in scores:
        products.append(product_score.to_dict())

    return {
        "source": source_name,
        "sector": sector,
        "date": date.today().isoformat(),
        "catalog_score": catalog_score,
        "ready": count_ready(scores),
        "product_count": len(scores),
        "criteria": criterion_percentages(scores),
        "products": products,
        "skipped_rows": errors,
    }

