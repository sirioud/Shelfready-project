# Nomades project

![nomades logo](https://nomades.ch/wp-content/themes/nomades_23/assets/imgs/logo-nomades.png)

## ppl_2026_3t2
## Flavia Sirioud
## sirioud@gmail.com

## Description

# ShelfReady

ShelfReady checks how well an online shop's product listings can be read by AI
shopping assistants such as Gemini or ChatGPT. It reads the shop's product CSV
export, gives each listing a score out of 100 and lists what to fix.

It is made for one sector, outdoor and sport gear, and uses that sector's
standards (for example the temperature ratings of sleeping bags) instead of
generic rules. It is free, needs no account or API key, and only reads the
CSV file.

It is a web page made with Streamlit, online at
https://shelfready-project.onrender.com. The page can also export an AI-ready
feed for Google Merchant Center (see below).

## Project structure

```
nomades_project/
├── shelfready_app.py         the Streamlit web page (display only)
├── requirements.txt          packages for the web page (Streamlit)
├── requirements-freeze.txt   the whole course environment, for the full Docker image
├── Dockerfile                the image used on Render
├── docs/                     testing guide, code notes, CSV references, sample data chart
├── tests/                    13 unittest tests on the core of the app
└── shelfready/               all the checking logic
    ├── loader.py             reads and validates the CSV
    ├── attributes.py         reads specs such as "volume_l: 30 | weight_g: 900"
    ├── models.py             Product and RuleResult
    ├── rules.py              the 14 rules and their points
    ├── scoring.py            score per listing and per catalog
    ├── questions.py          shopper questions a listing can or cannot answer
    ├── feed.py               the AI-ready feed
    ├── sector.py             the outdoor-gear knowledge, as data
    ├── report.py             HTML and JSON reports
    └── data/                 sample_products.csv, test_shop.csv
```
## Online version

The page is deployed on Render (free plan) as a Docker container built from the
`Dockerfile`: Python 3.12 slim, Streamlit, the app and the package. Tests and
docs are not copied into the image. Render's health check calls
`/_stcore/health`.

## The CSV file

| Column | Needed | Example |
|---|---|---|
| `id`, `title`, `price` | yes | `P001`, `Trail daypack 30 l`, `89.00` |
| `category` | no | `backpack`, `sleeping_bag`, `headlamp` |
| `description` | no | free text |
| `currency`, `availability` | no | `EUR`, `in_stock` |
| `gtin`, `brand`, `image_url` | no | `4006381333931`, `Nordwear`, `https://...` |
| `attributes` | no | `volume_l: 30 \| weight_g: 900 \| material: nylon` |

Prices can be written `89.00`, `89,00` or `59.-`. A row with no id, a
duplicate id or a price that is not a number is skipped and shown in the
report, and the other rows are still scored (`test_shop.csv` has one on
purpose). The web page has a template CSV to download.

## How the score works

Each listing goes through 14 rules. A rule gives all its points or none, and
the score is the sum of the points of the rules that pass. The rules are
grouped in five criteria:

| Criterion | What it checks | Points |
| --- | --- | --- |
| Distinctive attributes | the key specs of the category are there (e.g. volume and weight for a backpack) | 21 |
| Disambiguation | units, precise compatibility, pack size, valid barcode, Google feed requirements | 39 |
| Price / content coherence | the price, the text and the specs agree, and the values are realistic | 17 |
| Structuring | the specs are in attributes, not only in the description | 8 |
| Clear wording | facts instead of marketing words, no keyword stuffing, a clear first sentence | 15 |

A listing is ready from 90 points. Because the rules are all or nothing, this
means it has all the key specs of its category and at most one or two small
problems. A listing that Google Merchant Center would reject (no price, wrong
availability value, placeholder brand) is blocked and never counts as ready,
whatever its score. The points are set in `RULE_REGISTRY` in `rules.py`.

Some rules use industry standards: the GS1 check digit for barcodes, Google's
product data specification, EN ISO 23537 for sleeping bags (comfort, limit and
extreme temperatures, in that order) and the GEO research of
[Aggarwal et al. (KDD 2024)](https://arxiv.org/abs/2311.09735), which found
that numbers make a product more visible in AI answers while marketing words
and keyword stuffing do not. All sector knowledge is in `sector.py`, so the
tool can be adapted to another sector by replacing that file and the sample
CSV.

The report also lists typical shopper questions per category, such as "a
sleeping bag for a night at -5 °C". If a listing is missing the attribute
needed to answer, an assistant cannot show it for that question. These
questions are not part of the score, they explain what a missing attribute
costs.

The score cannot guarantee that an assistant will recommend a product. Reviews,
other websites and the live product page are not checked.

## AI-ready feed

Since May 2026, Google Merchant Center accepts "conversational attributes" that
AI Mode and Gemini read. ShelfReady writes two of them in a supplemental feed
(a TSV file, one line per product, matched to the shop's main feed by `id`):

- `product_highlight`, made from the attributes: `"Volume: 30 l", "Weight: 900 g"`
- `question_and_answer`, the shopper questions the listing can answer:
  `"Does it weigh less than 1 kg?":"Yes, weight is 900 g."`

Everything comes from the shop's own data. Questions that cannot be answered
are left out, and so are listings whose specs contradict the title or look
wrong. It is still worth checking the file against Google's
[product data specification](https://support.google.com/merchants/answer/7052112)
before uploading it.

## Tests

```bash
python -m unittest
```

13 tests. The two web page tests only run where Streamlit is installed
(`nomades_nppd_312`) and are skipped elsewhere. See [TESTING.md](docs/TESTING.md).

Code style: constants in `UPPER_CASE` (PEP 8), functions and variables in
`snake_case`, classes in `CamelCase`, typed variables.

## Comparison with existing tools

Some tools already score shop catalogs for AI readiness (checked October 2026):

| Tool | What it checks | Difference |
| --- | --- | --- |
| Channable AI Readiness Audit | whether the attributes used by Google's AI are filled in | paid platform, same rules for every product |
| Product Feed Scan | six dimensions on an uploaded feed | does not check barcode check digits or contradictions between title and attributes |
| SKAW (Shopify app) | missing GTINs, weak descriptions, thin specs | Shopify only, from $19.99/month |
| Exatio Catalog Audit, FeedProof | empty fields before a Merchant Center upload | completeness only |

Most of these tools check whether fields are filled in. ShelfReady also checks
whether the information is precise and consistent enough to compare products,
using the standards of one sector. For example, listing P003 in the sample file
has every field filled in but scores 71, because its brightness and battery
runtime are only written in the description.

ShelfReady does not read Shopify or XML exports directly, check the live
product page, or use Google's own attribute weights, which some of these tools
do.


