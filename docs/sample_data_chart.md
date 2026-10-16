# Sample data — what each row tests

Reference for `shelfready/data/sample_products.csv`. The fake shop sells
**outdoor and sport gear**. Every row exists to make one rule fire, so the demo
can show a real failure for each of the four criteria. Keep this next to the
file: if a score changes unexpectedly, this is where you check what the row was
supposed to do.

## The rows

| Row      | Weakness                                                                  | Criterion                  | Score |
| -------- | ------------------------------------------------------------------------- | -------------------------- | ----- |
| P001     | none — the reference listing                                              | —                          | 100   |
| P002     | sleeping bag with only the comfort temperature; EN ISO 23537 limit and extreme ratings missing | attributes | 80 |
| P003     | headlamp with one attribute; lumens and runtime sit in the prose          | attributes, structuring    | 65    |
| P004     | "under 75" — 75 what?                                                     | disambiguation             | 88    |
| P005     | "compatible with most gas cartridges"; fuel and weight missing            | disambiguation, attributes | 67    |
| P006     | pack of 2 announced, no `pack_size` field                                 | disambiguation             | 95    |
| P007     | €129 for a four-word description                                          | coherence                  | 95    |
| (no id)  | skipped by the loader                                                     | —                          | —     |
| P009     | title says 25 l, attribute says 30; bad check digit                       | coherence, disambiguation  | 80    |
| P010     | set of 6, no `pack_size` field                                            | disambiguation             | 95    |
| P011     | price is `abc`, skipped by the loader                                     | —                          | —     |
| P012     | availability "available" and brand "N/A" break the Merchant Center spec — **blocked**, not ready despite 90 | disambiguation | 90 |

Catalog score: **85.5 / 100**, 4 listings of 10 likely to be recommended,
2 rows skipped, 4 shopper questions that cannot be matched (P002 once, P003
twice, P005 once).

## The four criteria

| Criterion                 | Question it asks                                          | Rules                                                          | Points |
| ------------------------- | --------------------------------------------------------- | -------------------------------------------------------------- | ------ |
| Distinctive attributes    | Can an AI tell this apart from another of the same type?   | `expected_attributes`, `attribute_count`                        | 25     |
| Disambiguation            | Is there anything the AI cannot resolve?                   | `units`, `compatibility`, `quantity`, `gtin`, `feed_standard`   | 45     |
| Price / content coherence | Does the listing contradict itself or reality?             | `price_coherence`, `spec_agreement`, `plausible_values`         | 20     |
| Structuring               | Is the information in fields or buried in prose?           | `structured_share`                                              | 10     |

## Two typing traps

The row before P009 **starts with a comma**. That empty id is deliberate — the
loader must skip it and report line 9.

P009's barcode ends in **2** where P001's ends in **1**. That single digit is
what makes the GTIN check digit fail.

## The rows to show in the demo

**P003 — the argument in one row.** It has a brand, a full description, a valid
barcode. It passes every check a completeness plugin would run, and still
scores 65, because "400 lm" and "20 h" sit in a sentence rather than in
`lumens_lm: 400 | runtime_h: 20`. Replace its attributes with
`lumens_lm: 400 | runtime_h: 20 | weight_g: 85 | material: aluminium` and it
goes to 100; the catalog rises from 85.5 to 89.0, and the two headlamp
shopper questions can now be matched. That is a fix no completeness
checker would ever ask for.

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

Otherwise `test_cli.py`, which asserts the catalog score of 85.5 and 4 of 10,
will fail.
