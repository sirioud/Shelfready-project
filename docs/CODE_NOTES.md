# ShelfReady — Code Notes

Error handling, validation, and clean-code summary for the app.

## Error handling

The app uses **two deliberate levels** of error handling.

### 1. Whole-file errors — stop the run (`LoaderError`)

A custom exception (`loader.py`) raised when nothing can be scored:

- **Bad encoding** — tries UTF-8, then latin-1, otherwise raises
  "save it as CSV UTF-8 and try again".
- **File not found / not a file** (e.g. a folder was passed).
- **Missing required columns** — `id`, `title`, `price`.

It is caught in exactly the two entry points:

| Entry point | Location | What the user sees |
|---|---|---|
| CLI | `__main__.py` | `Error: …` printed to **stderr**, non-zero exit |
| Web | `shelfready_app.py` (`load_input`) | `st.error("This file cannot be read. …")`, returns `None` |

### 2. Row-level errors — skip the row, keep going

A single bad row never kills the run (`loader.py`). Each problem is appended
to an `errors` list and the row is `continue`d:

- missing `id`
- duplicate `id` (names the earlier line)
- `price` is not a number

These strings resurface in the UI under **"Rows that could not be read"**
and in both the HTML and JSON reports. One broken row does not cost you the
other listings.

**Pattern:** *raise to abort the whole file, collect-and-continue for an
individual row.*

## Validation

"Validator" means two different things in this project:

- **ShelfReady rules** (`shelfready/rules.py`) — the `check_*` functions.
  Each validates one product against one rule and returns a
  `RuleResult(passed, points, message)`. They **do not raise**: they report
  pass/fail plus a fix message, which suits data that is "wrong" but readable
  (e.g. `is_valid_gtin` checksum, unit checks, price/content coherence).
- **WTForms validators** (Flask exercise, `forms/login.py`) — `DataRequired`,
  `Length`, `Email`, `EqualTo`, plus custom `validate_images_extensions` and
  `validate_password`. These **do raise** `ValidationError`, which WTForms
  turns into field errors. (Separate project, listed for contrast.)

## Clean-code summary

What the codebase does well:

- **Single-responsibility modules** — `loader` reads, `rules` checks,
  `scoring` aggregates, `report` formats, `questions` matches shopper intent,
  `sector` holds domain data, `models` holds the two data classes.
- **Typed signatures and variables** throughout.
- **No duplicated logic** — shared constants (e.g. `Quantity_phrase`,
  `Criteria`) live in one module and are imported, not copied.
- **Defensive loader** — the two-level error handling above; nothing trusts
  the input file.
- **Escaped HTML** in the report (`escape(...)`) — no injection from product
  text.
- **Naive, readable style on purpose** — explicit loops over comprehensions
  and lambdas, matching the course convention.
- **`Capitalized_case` constants**, lowercase locals — consistent naming.
- **`AuditResult`** bundles everything one audit produces, so results travel
  as a single value; `main()` is pure orchestration and every `show_*`
  function takes that one object.

Recent clean-code passes:

- `is_valid_gtin` — reversed the digit list so the loop index *is* the weight
  position (no descending range + counter).
- `models.py` — both `__repr__`s use f-strings, matching the rest of the code.
- `AuditResult` refactor — extracted `load_input()` from `main()`.

Deferred / optional (style calls, not clear wins):

- `most_common_problems` (`scoring.py`) uses a manual find-the-max loop; a
  sort would be shorter but less in keeping with the naive style.

## Implemented improvements (senior review)

Two structural improvements from the code review, now applied.

### 1. One source of truth for rule registration

**Before:** a rule's identity was spread across three structures — `All_rules`
(the run list) and `Points` (`rules.py`), plus `Criterion_of_rule`
(`report.py`). Adding or renaming a rule meant editing all three in two files;
forgetting one gave a silent wrong total or a runtime `KeyError`.

**After:** a single `Rule_registry` in `rules.py` holds, per rule, its
function, its points, and its criterion. `All_rules`, `Points`, and
`Criterion_of_rule` are **derived** from it, so they cannot drift apart.
`report.py` now imports `Criterion_of_rule` instead of keeping its own copy.

```python
Rule_registry: list[tuple] = [
    (check_expected_attributes, 17, "Distinctive attributes"),
    (check_gtin, 8, "Disambiguation"),
    ...
]
All_rules = [entry[0] for entry in Rule_registry]
Points = {rule_name(entry[0]): entry[1] for entry in Rule_registry}
Criterion_of_rule = {rule_name(entry[0]): entry[2] for entry in Rule_registry}
```

Adding a rule is now: write the `check_` function, add **one line** to the
registry. The three presentation dicts in `report.py` (`Rule_names`,
`How_to_fix`, `Basis_of_rule`) are UI copy and stay there; a test already
checks they cover every registered rule.

### 2. Parse each product's attributes once

**Before:** nearly every rule called `parse_attributes(product.attributes)`
again from scratch, and re-concatenated `product.title + " " + description`.
The same string was parsed a dozen-plus times per product.

**After:** `Product` gained two accessors:
- `product.attrs()` — parses the attributes column once and caches the result
  (`_parsed`), reused on every later call.
- `product.text()` — title and description joined, the free text most rules
  scan.

`rules.py`, `questions.py`, and `feed.py` now call these instead of parsing
directly. Clearer call sites and the parsing work happens once per product.

**Verification:** full suite green — `Ran 94 tests ... OK (skipped=2)` (the two
skips are the Streamlit-only app tests). Points still sum to 100, `All_rules`
names equal `Points` keys, `report` shares the one criterion map, and
`attrs()` returns the same cached object on repeat calls.

### Still open (not implemented)

- Replace the hand-rolled counting loops (`most_common_problems`,
  `check_keyword_stuffing`, `count_ready`) with `collections.Counter` /
  `sum(...)` — deferred to keep the course's naive style.
- Cache `unanswered_questions` on `ProductScore` (computed 3–4 times today).
- Tighten loose types: `All_rules` -> `list[Callable[[Product], RuleResult]]`;
  `TypedDict` for report/row dict shapes.

## Tests

94 tests (`unittest`), all passing (2 Streamlit-only app tests skipped when
Streamlit is absent).
