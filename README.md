# Nomades project

![nomades logo](https://nomades.ch/wp-content/themes/nomades_23/assets/imgs/logo-nomades.png)

## ppl_2026_3t2
## Flavia Sirioud
## sirioud@gmail.com

## Description


# ShelfReady

ShelfReady scores product listings for **AI readability**: how likely an AI
shopping assistant is to understand a listing, compare it with others and
recommend it. It reads a shop's product CSV export and gives a score, a report
and a list of fixes, listing by listing.

It can be used two ways, with the same checks and the same scores:

- a **web page** (Streamlit) for shop owners: upload a CSV, read the results, download the report;
- a **command line** tool: `python -m shelfready audit FILE.csv`.

Both can also write an **AI-ready feed**: a Google Merchant Center supplemental
feed, made from the shop's own specs, that AI Mode and Gemini read (see
[GEO and the AI-ready feed](#geo-and-the-ai-ready-feed)).

It is built for one industry, **outdoor and sport gear**, and checks listings
against that sector's standards rather than applying generic rules.

## Principles

- **Free and offline:** no account, no API key, no network. Catalog data stays on your computer, the web page included.
- **Light:** the checks use the Python standard library only (Python 3.10 or newer). Only the web page needs Streamlit.
- **Read-only:** the tool only reads the CSV. The shop and the original file are never changed.

## Project structure

```
nomades_project/
├── shelfready_app.py        the Streamlit web page (display only)
├── requirements.txt         packages to install (Streamlit)
├── README.md
├── docs/
│   ├── TESTING.md           how the tests work
│   ├── CODE_NOTES.md        notes on the code and review changes
│   ├── real_world_csv_reference.md
│   └── sample_data_chart.md what is in the sample CSV
├── tests/                   94 unittest tests, one file per module
└── shelfready/              the package: all the checking logic
    ├── __main__.py          command line (python -m shelfready)
    ├── loader.py            reads and validates the CSV
    ├── attributes.py        reads specs such as "volume_l: 30 | weight_g: 900"
    ├── models.py            Product and RuleResult
    ├── rules.py             the rules and their points
    ├── scoring.py           score per listing and per catalog
    ├── questions.py         shopper questions a listing can or cannot match
    ├── feed.py              the AI-ready feed for Google Merchant Center
    ├── sector.py            all the outdoor-gear knowledge, as data
    ├── report.py            terminal, HTML and JSON reports
    └── data/                sample_products.csv, test_shop.csv
```

## Web page

The web page needs Streamlit, which is installed in the course environment
`nomades_python_env` (container), conda environment `nomades_nppd_312`:

```bash
conda activate nomades_nppd_312
streamlit run shelfready_app.py
```

Outside the course container, install it with `pip install -r requirements.txt`.

Open the address it prints (usually http://localhost:8501). When running in
the container, VS Code forwards the port automatically.

Upload a CSV, or tick **Try the sample outdoor shop instead**.

| Part of the page | What it shows |
|---|---|
| Side bar | How it works in 4 steps, the columns the file needs, a **template CSV** to download, the categories that are checked |
| Verdict | Catalog score and number of ready listings, in green (90 or more), orange (70 or more) or red |
| **Overview** tab | AI readability score, ready listings, shopper questions not matched; the score per criterion with a progress bar; the 3 most common problems to **fix first** |
| **Listings** tab | A table of listings sorted worst first, with a status (✅ Ready, 🔧 To fix, ⛔ Blocked). For each listing that needs work: every problem, how to fix it, the industry reference behind it, and the shopper questions it cannot match. A toggle hides the ready listings |
| **Shopper questions** tab | Each typical request, the listings that match it and the ones that cannot be matched |
| **Download** tab | The HTML report, the results as JSON and the **AI-ready feed** (TSV); the rows of the file that could not be read |

The page only displays results. All the checking is done by the `shelfready`
package, the same code the `audit` command uses, so both always give the same
scores. The file is never sent anywhere.

## Command line

Run every command from the root of the repository.

```bash
python -m shelfready audit shelfready/data/sample_products.csv
python -m shelfready audit shelfready/data/sample_products.csv --html shelfready/reports/report.html
python -m shelfready audit shelfready/data/sample_products.csv --feed shelfready/reports/ai_feed.tsv
```

`audit` prints the catalog score, the most common problems and one line per
listing. With `--html PATH`, it also writes a report that opens in a browser,
with a score per criterion and the industry reference behind each problem.
With `--feed PATH`, it writes the AI-ready feed.

## The CSV file

| Column | Needed | Example |
|---|---|---|
| `id`, `title`, `price` | yes | `P001`, `Trail daypack 30 l`, `89.00` |
| `category` | no | `backpack`, `sleeping_bag`, `headlamp` |
| `description` | no | free text |
| `currency`, `availability` | no | `EUR`, `in_stock` |
| `gtin`, `brand`, `image_url` | no | `4006381333931`, `Nordwear`, `https://...` |
| `attributes` | no | `volume_l: 30 \| weight_g: 900 \| material: nylon` |

Prices can be written `89.00`, `89,00` or the Swiss way `59.-`. Rows with a
missing id, a duplicate id or a price that is not a number are skipped and
listed in the report. `shelfready/data/test_shop.csv` contains such a row on
purpose. The web page offers a template to download.

## Tests

```bash
python -m unittest
```

94 tests. The two web page tests run only in an environment with Streamlit
(`nomades_nppd_312`); elsewhere they are skipped. See [TESTING.md](docs/TESTING.md)
for how the tests work and how to add one.

## Code style

Constants use `Capitalized_case` (`Pass_score`, `Sample_file`), functions and
variables `snake_case`, classes `CamelCase`. Variables are typed
(`score: int = 90`).

## The five criteria

| Criterion | Question it asks | Rules | Points |
| --- | --- | --- | --- |
| Distinctive attributes | Can an AI tell this product apart from another of the same type? | `expected_attributes`, `attribute_count` | 21 |
| Disambiguation | Is there anything the AI cannot resolve? | `units`, `compatibility`, `quantity`, `gtin`, `feed_standard` | 39 |
| Price / content coherence | Does the listing contradict itself or reality? | `price_coherence`, `spec_agreement`, `plausible_values` | 17 |
| Structuring | Is the information in fields or buried in prose? | `structured_share` | 8 |
| Clear wording | Is the text written for an AI assistant? | `facts_not_claims`, `keyword_stuffing`, `clear_opening` | 15 |

A listing counts as likely to be recommended from 90 points (`Pass_score` in
`scoring.py`), unless it is **blocked**: a listing that fails `feed_standard`
(no title, no price, wrong availability, placeholder brand) would be rejected
by Google Merchant Center, so it is never ready, whatever its score. Point
values are in `rules.py`.

`plausible_values` checks that numbers make sense for the sector: each value in
its usual range (a `weight_g` of 1.2 is a weight in kg in the wrong field), and
sleeping bag temperatures in the EN ISO 23537 order, comfort > limit > extreme.
`spec_agreement` compares the numbers of both the title and the description with
the attributes: "holds 25 l" next to `volume_l: 30` is a contradiction.

## Shopper questions

`sector.py` lists typical questions a shopper asks an AI assistant, per
category: "a sleeping bag for a night at -5 °C", "a headlamp of 300 lm or
more". For each listing the report says whether it matches, does not match, or
**cannot be matched** because the attribute is missing. A listing that cannot
be matched may fit perfectly, but an assistant will never show it. The
questions do not change the score; they show the shop what the score means.

## GEO and the AI-ready feed

GEO (Generative Engine Optimization) is SEO for AI assistants: the goal is to
be cited in the assistant's answer. The research behind it ([Aggarwal et al.,
KDD 2024](https://arxiv.org/abs/2311.09735)) found that numbers raise
visibility, an authoritative tone does not, and keyword stuffing lowers it.
The "Clear wording" criterion turns this into three rules:

| Rule | Fails when | Example of a fix |
| --- | --- | --- |
| `facts_not_claims` | 2 or more marketing words ("premium", "ultimate"...) and fewer numbers with units | "ultra-light" becomes "weighs 780 g" |
| `keyword_stuffing` | a word of 4 letters or more repeated in the title, 3 commas or more, or more than 150 characters | "Tent pegs aluminium tent pegs" becomes "Aluminium tent pegs set of 6" |
| `clear_opening` | the first sentence of the description does not name the product type (categories in `sector.py`) | "Boils a litre quickly" becomes "Pocket gas stove that boils a litre..." |

The word lists are in `sector.py`. The rules suggest; the shop owner writes. No
AI rewrites the text, so ShelfReady stays free and offline.

**AI-ready feed.** Since May 2026, Google Merchant Center accepts
"conversational attributes" that AI Mode and Gemini read. ShelfReady writes two
of them, as a supplemental feed (one line per product, joined to the main feed
by `id`):

| Column | Made from | Example |
| --- | --- | --- |
| `product_highlight` | the attributes, at least 2 | `"Volume: 30 l", "Weight: 900 g", "Material: nylon"` |
| `question_and_answer` | the shopper questions the listing can answer, yes or no | `"Does it weigh less than 1 kg?":"Yes, weight is 900 g."` |

Nothing is invented: a question whose attribute is missing is left out, and a
listing whose specs contradict its title or look implausible is left out until
it is fixed. The file is tab separated, so a comma inside a value cannot split
it. Check the file before uploading it, and confirm the attribute rules on
Google's [product data specification](https://support.google.com/merchants/answer/7052112).

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
the sample file has every field filled and still scores 71, because its light
output and runtime are written in the description instead of in attributes.

What the other tools do that ShelfReady does not: read Shopify or XML exports
directly, check the live product page (schema.org, robots.txt), and follow
Google's published attribute weights.
