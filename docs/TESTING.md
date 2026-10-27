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
python -m unittest tests.test_scoring.ScoringTests.test_perfect_product_scores_100  # one test only
```

In VS Code, the tests also appear in the **Testing** panel (flask icon in the
side bar). `.vscode/settings.json` already configures it.

### Reading the result

```
ss...........
----------------------------------------------------------------------
Ran 13 tests in 0.010s

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

The tests are in `tests/`. Only the core of the app is tested: one or two
tests for each important part.

| File | Tests | Module tested | What it checks |
|---|---|---|---|
| `test_loader.py` | 4 | `loader.py` | A missing column stops the file (`LoaderError`); a bad price skips only its row; Swiss prices (`1'299.00`, `89.-`, `1 299,50`); `nan` and `inf` refused |
| `test_rules.py` | 3 | `rules.py` | GTIN check digit (valid codes, wrong last digit); the rule points add up to 100 |
| `test_scoring.py` | 3 | `scoring.py` | A perfect listing scores 100; a broken one loses points for the right rules; a blocked listing is not ready even at 90 |
| `test_report.py` | 1 | `report.py` | Text from the shop's file is escaped in the HTML report |
| `test_app.py` | 2 | `shelfready_app.py` | The web page starts, and the sample shop gives 85.3 / 100, 5 of 10 ready and the 2 skipped rows |
| **Total** | **13** | | |

The tests give the CSV to the loader as text, so running the tests never
changes the files in `shelfready/data/`.

## Skipped tests

`test_app.py` needs Streamlit. It is installed only in the course environment
`nomades_nppd_312`. In any other environment the two app tests are **skipped**,
not failed:

```python
@unittest.skipUnless(Has_streamlit, "streamlit is not installed in this environment")
```

Run the tests in `nomades_nppd_312` to see all 13 pass.

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
