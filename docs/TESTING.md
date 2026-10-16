# Testing ShelfReady

ShelfReady is tested with `unittest`, the test framework that comes with
Python. Nothing extra needs to be installed, except Streamlit for the two
web page tests.

## Running the tests

Run every command from the root of the repository (the folder that contains
`shelfready_app.py`).

```bash
conda activate nomades_nppd_312                  # environment with Streamlit
python -m unittest                               # all tests
python -m unittest -v                            # one line per test, with its name
python -m unittest tests.test_scoring # one file only
python -m unittest tests.test_scoring.ScoringTests.test_catalog_average  # one test only
```

In VS Code, the tests also appear in the **Testing** panel (flask icon in the
side bar). `.vscode/settings.json` already configures it.

### Reading the result

```
ss..................................................................
----------------------------------------------------------------------
Ran 94 tests in 0.032s

OK (skipped=2)
```

| Symbol | Meaning |
|---|---|
| `.` | test passed |
| `F` | test failed: the code gave a different answer than expected |
| `E` | test crashed: an error happened while running it |
| `s` | test skipped (see [Skipped tests](#skipped-tests)) |

`OK` at the end means everything passed. Otherwise unittest lists each failing
test with the expected value and the value it actually got.

## How a test is written

Example from `tests/test_scoring.py`:

```python
import unittest

from shelfready.scoring import score_product
from tests.helpers import good_product


class ScoringTests(unittest.TestCase):
    def test_perfect_product_scores_100(self):
        result = score_product(good_product())   # 1. run the code
        self.assertEqual(result.score, 100)      # 2. check the answer
        self.assertTrue(result.is_ready)
```

- A **class** that inherits from `unittest.TestCase` groups related tests.
- Every method whose name starts with **`test_`** is one test. unittest finds
  and runs them automatically.
- Every file whose name starts with **`test_`** is searched for tests.
- The **`assert...`** methods are the checks:

| Method | The test passes if |
|---|---|
| `assertEqual(a, b)` | `a == b` |
| `assertTrue(x)` / `assertFalse(x)` | `x` is true / false |
| `assertLess(a, b)` | `a < b` |
| `assertIn(x, container)` | `x` is in `container` |
| `assertRaises(Error)` | the code raises `Error` |

## The helper: `good_product()`

`tests/helpers.py` builds a **perfect listing** that passes every
rule. A test gives keyword arguments to break only the field it wants to check:

```python
good_product()                         # perfect listing: score 100
good_product(gtin="")                  # same listing without a barcode
good_product(brand="N/A")              # same listing with a placeholder brand
good_product(title="Trail daypack 25 l")  # title disagrees with volume_l: 30
```

Because everything else in the listing is correct, a failing test points to
exactly one cause.

## What is tested

The tests are in `tests/`. There is one test file per module.

| File | Tests | Module tested | What it checks |
|---|---|---|---|
| `test_rules.py` | 34 | `rules.py` | Each rule (GTIN, brand, specs, marketing words, keyword stuffing, ...) on good and broken listings |
| `test_loader.py` | 13 | `loader.py` | Reading CSV files: missing columns, invalid prices, skipped rows |
| `test_attributes.py` | 11 | `attributes.py` | Reading specs such as `volume_l: 30 \| weight_g: 900` |
| `test_scoring.py` | 8 | `scoring.py` | Listing score, catalog average, "ready" and "blocked" listings |
| `test_report.py` | 8 | `report.py` | The HTML and JSON reports |
| `test_cli.py` | 5 | `__main__.py` | The `python -m shelfready audit` command, with `--html` and `--feed` |
| `test_questions.py` | 4 | `questions.py` | Which shopper questions a listing can answer |
| `test_app.py` | 2 | `shelfready_app.py` | The Streamlit web page |
| `test_feed.py` | 9 | `feed.py` | The AI-ready feed: highlights, questions and answers, file format, listings left out |
| **Total** | **94** | | |

Tests that need a file (CSV input, HTML report) create it in a temporary
folder with `tempfile`, so running the tests never changes the files in
`shelfready/data/`.

## Skipped tests

`test_app.py` needs Streamlit. It is installed only in the course environment
`nomades_nppd_312`. In any other environment the two app tests are **skipped**,
not failed:

```python
@unittest.skipUnless(Has_streamlit, "streamlit is not installed in this environment")
```

Run the tests in `nomades_nppd_312` to see all 94 pass.

## Adding a test

1. Open the test file of the module you changed (for `rules.py`, `test_rules.py`).
2. Add a method starting with `test_` to the class, with a name that says what
   it checks:

   ```python
   def test_missing_brand_fails(self):
       result = score_product(good_product(brand=""))
       self.assertLess(result.score, 100)
   ```

3. Run `python -m unittest -v` and check that the new test appears and passes.

Run all the tests after every change. If all of them still pass, the change
did not break anything that is tested.
