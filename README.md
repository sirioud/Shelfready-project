# ShelfReady

ShelfReady is a command-line Python tool that scores product listings for **AI
readability**: how likely an AI shopping assistant is to understand a listing,
compare it with others and recommend it. It reads a shop's product CSV export
and prints a score, a report and a short list of fixes.

It is built for one industry, **outdoor and sport gear**, and checks listings
against that sector's standards rather than applying generic rules.

## Principles

- **Free and offline:** no account, no API key, no network. Catalog data stays on your computer.
- **Standard library only:** nothing to install beyond Python 3.10 or newer.
- **Read-only:** the tool only reads the CSV. The shop and the original file are never changed.

## Usage

Run every command from the root of the repository.

```bash
python -m shelfready audit shelfready/data/sample_products.csv
python -m shelfready audit shelfready/data/sample_products.csv --html shelfready/reports/report.html
```

`audit` prints the catalog score, the most common problems and one line per
listing. With `--html PATH`, it also writes a report that opens in a browser,
with a score per criterion and the industry reference behind each problem.

## Web page

The same checks are also available as a local web page, built with Streamlit.
It needs the course environment that has Streamlit installed:

```bash
conda activate nomades_nppd_312
streamlit run shelfready_app.py
```

Open the address it prints (usually http://localhost:8501), upload a CSV or
tick the sample shop. The page shows the score, the score per criterion, what
to fix first, the shopper questions and one line per product, and lets you
download the HTML report or the results as JSON. The page runs on your
computer: the file is never sent anywhere.

The page only displays results. All the checking is done by the `shelfready`
package, the same code the `audit` command uses, so both always give the same
scores.

## Tests

```bash
python -m unittest
```

The two web page tests run only in an environment with Streamlit
(`nomades_nppd_312`); elsewhere they are skipped.

## The four criteria

| Criterion                 | Question it asks                                          | Rules                                                          | Points |
| ------------------------- | --------------------------------------------------------- | -------------------------------------------------------------- | ------ |
| Distinctive attributes    | Can an AI tell this product apart from another of the same type? | `expected_attributes`, `attribute_count`                 | 25     |
| Disambiguation            | Is there anything the AI cannot resolve?                   | `units`, `compatibility`, `quantity`, `gtin`, `feed_standard`   | 45     |
| Price / content coherence | Does the listing contradict itself or reality?             | `price_coherence`, `spec_agreement`, `plausible_values`         | 20     |
| Structuring               | Is the information in fields or buried in prose?           | `structured_share`                                              | 10     |

A listing counts as likely to be recommended from 90 points (`PASS_SCORE` in
`scoring.py`), unless it is **blocked**: a listing that fails `feed_standard`
(no title, no price, wrong availability, placeholder brand) would be rejected
by Google Merchant Center, so it is never ready, whatever its score. Point
values are in `rules.py`.

`plausible_values` checks that numbers make sense for the sector: each value in
its usual range (a `weight_g` of 1.2 is a weight in kg in the wrong field), and
sleeping bag temperatures in the EN ISO 23537 order, comfort > limit > extreme.

## Shopper questions

`sector.py` lists typical questions a shopper asks an AI assistant, per
category: "a sleeping bag for a night at -5 °C", "a headlamp of 300 lm or
more". For each listing the report says whether it matches, does not match, or
**cannot be matched** because the attribute is missing. A listing that cannot
be matched may fit perfectly, but an assistant will never show it. The
questions do not change the score; they show the shop what the score means.

## Sector and industry standards

All sector knowledge sits in `shelfready/sector.py`, as data. To audit another
sector, replace that file and the sample CSV.

| Standard | What the tool checks |
| --- | --- |
| GS1 check digit (also required by Google Merchant Center) | `gtin`: the barcode is valid, so a listing can be matched across shops |
| Google Merchant Center product data specification | `feed_standard`: accepted availability values, no placeholder brand; size, colour, gender and age group for footwear and clothing |
| EN ISO 23537 (sleeping bags) | `expected_attributes`: comfort, limit and extreme temperatures; `plausible_values`: they go down in that order |
| schema.org Product (design reference) | `structured_share`: facts in dedicated fields rather than in prose |

The rules follow current GEO (Generative Engine Optimization) guidance. They
cannot guarantee that an assistant will recommend a product, and they cannot
check reviews, mentions on other websites or the live product page.

## How ShelfReady differs from existing tools

AI-readiness scoring for shops already exists (checked October 2026):

| Tool | What it checks | Where ShelfReady differs |
| --- | --- | --- |
| Channable AI Readiness Audit (launched 1 Oct 2026) | Whether the attributes Google's AI Mode and Gemini use are filled in; score out of 100 | Same checks for every product, inside a paid platform. ShelfReady uses one industry's standards |
| Product Feed Scan | Six dimensions (identity, content, taxonomy, variants, assets, enrichment) on an uploaded feed | Says itself that it does not check GTIN check digits, title/attribute contradictions or meaning. ShelfReady does all three |
| SKAW (Shopify app) | Missing GTINs, weak descriptions, thin specs; score out of 100 | Shopify only, from $19.99/month, generic rules |
| Exatio Catalog Audit, FeedProof (WooCommerce) | Empty fields before a Google Merchant Center upload | Completeness only |

**These tools check that the fields an AI uses are filled in, with the same
rules for every product. ShelfReady checks whether the information is precise
and consistent enough to be compared (units, contradictions, valid barcodes)
against the standards of one industry, offline and for free.** Listing P003 in
the sample file has every field filled and still scores 65, because its light
output and runtime are written in the description instead of in attributes.

What the other tools do that ShelfReady does not: read Shopify or XML exports
directly, check the live product page (schema.org, robots.txt), and follow
Google's published attribute weights.
