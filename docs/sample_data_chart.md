# Sample data — what each row tests

Reference for `shelfready/data/sample_products.csv`. The fake shop sells
**outdoor and sport gear**. Every row exists to make one rule fire, so the demo
can show a real failure for each of the five criteria. Keep this next to the
file: if a score changes unexpectedly, this is where you check what the row was
supposed to do.

## The rows

| Row      | Weakness                                                                  | Rules that fail (points lost)                                   | Score |
| -------- | ------------------------------------------------------------------------- | --------------------------------------------------------------- | ----- |
| P001     | none — the reference listing                                              | —                                                               | 100   |
| P002     | sleeping bag with only the comfort temperature; EN ISO 23537 limit and extreme ratings missing | `expected_attributes` (17)                  | 83    |
| P003     | headlamp with one attribute; lumens and runtime sit in the prose          | `expected_attributes` (17), `attribute_count` (4), `structured_share` (8) | 71 |
| P004     | "under 75" — 75 what?                                                     | `units` (10)                                                    | 90    |
| P005     | "compatible with most gas cartridges"; fuel and weight missing; the first sentence never says "stove" | `expected_attributes` (17), `attribute_count` (4), `compatibility` (6), `clear_opening` (5) | 68 |
| P006     | pack of 2 announced, no `pack_size` field                                 | `quantity` (5)                                                  | 95    |
| P007     | €129 with a description under 120 characters; "premium" and "best" instead of facts | `price_coherence` (4), `facts_not_claims` (6)          | 90    |
| (no id)  | skipped by the loader                                                     | —                                                               | —     |
| P009     | title and description say 25 l, attribute says 30; bad check digit        | `gtin` (8), `spec_agreement` (9), `structured_share` (8)        | 75    |
| P010     | set of 6, no `pack_size` field; "tent" and "pegs" repeated in the title   | `quantity` (5), `keyword_stuffing` (4)                          | 91    |
| P011     | price is `abc`, skipped by the loader                                     | —                                                               | —     |
| P012     | availability "available" and brand "N/A" break the Merchant Center spec — **blocked**, not ready despite 90 | `feed_standard` (10)           | 90    |

Catalog score: **85.3 / 100**, **5** listings of 10 likely to be recommended
(P001, P004, P006, P007, P010), 2 rows skipped (lines 9 and 12), 4 shopper
questions that cannot be matched (P002 once, P003 twice, P005 once).

A listing is ready from 90 points, unless it is blocked. Because a rule gives
all its points or none, 90 means at most 10 points lost: one medium problem
(P004) or two small ones (P007, P010). A listing missing its key specs loses
17 points and can never be ready (P002).

## The five criteria

| Criterion                 | Question it asks                                          | Rules                                                          | Points | Sample catalog |
| ------------------------- | --------------------------------------------------------- | -------------------------------------------------------------- | ------ | -------------- |
| Distinctive attributes    | Can an AI tell this apart from another of the same type?   | `expected_attributes`, `attribute_count`                        | 21     | 72%            |
| Disambiguation            | Is there anything the AI cannot resolve?                   | `units`, `compatibility`, `quantity`, `gtin`, `feed_standard`   | 39     | 89%            |
| Price / content coherence | Does the listing contradict itself or reality?             | `price_coherence`, `spec_agreement`, `plausible_values`         | 17     | 92%            |
| Structuring               | Is the information in fields or buried in prose?           | `structured_share`                                              | 8      | 80%            |
| Clear wording             | Is the text written for an AI assistant?                   | `facts_not_claims`, `keyword_stuffing`, `clear_opening`         | 15     | 90%            |

"Sample catalog" is the share of that criterion's points the ten listings
earn together (`criterion_percentages` in `report.py`). Distinctive attributes
is the weakest, so that is where this shop should start.

## Two typing traps

The row before P009 **starts with a comma**. That empty id is deliberate — the
loader must skip it and report line 9.

P009's barcode ends in **2** where P001's ends in **1**. That single digit is
what makes the GTIN check digit fail.

## The rows to show in the demo

**P003 — the argument in one row.** It has a brand, a full description, a valid
barcode. It passes every check a completeness plugin would run, and still
scores 71, because "400 lm" and "20 h" sit in a sentence rather than in
`lumens_lm: 400 | runtime_h: 20`. Replace its attributes with
`lumens_lm: 400 | runtime_h: 20 | weight_g: 85 | material: aluminium` and it
goes to 100; the catalog rises from 85.3 to 88.2, 6 listings of 10 are ready,
and the two headlamp shopper questions can now be matched. That is a fix no
completeness checker would ever ask for.

**P002 — the industry standard.** Nothing is empty, but a sleeping bag sold
with only a comfort temperature cannot be compared under EN ISO 23537, which
labels comfort, limit and extreme. A generic checker does not know that.

**P012 — blocked.** It scores 90, enough to pass, but its availability
"available" and brand "N/A" would make Google Merchant Center reject it. A
blocked listing is never counted as ready, whatever its score.

**P009 — nothing is missing, yet it contradicts itself.** The title says 25 l,
the attribute says 30. An assistant comparing backpacks cannot tell which is
true, so it drops the listing. Completeness scoring has no way to see this at
all.

## If the scores drift

The expected numbers in the guide assume this file exactly. After editing it
for a demo, restore it with:

```
git checkout shelfready/data/sample_products.csv
```

Otherwise `test_app.py`, which asserts the catalog score of 85.3 and 5 of 10,
will fail.
