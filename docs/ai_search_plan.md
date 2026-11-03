# AI search test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An optional "AI search test" tab that asks Gemini to pick products for shopper needs and compares its picks with what the specs prove, to show benefit clarity.

**Architecture:** A new module `shelfready/ai_search.py` (Gemini only, no provider classes: `ask_gemini()` + a recorded run) reuses `answer_question()` from `questions.py` as the ground truth. The web page gets a fifth tab; the sample shop replays a recorded run. Nothing touches the 14 rules or the score.

**Tech Stack:** Python 3.12, `google-genai`, Streamlit 1.66.1, `unittest`.

**Spec:** `docs/ai_search_design.md`

## Global Constraints

- Model: `AI_MODEL = "gemini-3.5-flash"` (3.8 Flash was overloaded, 503, on 2–3 Nov). Key: environment variable `GEMINI_API_KEY` first (Render), else `config/gemini_creds.json` = `{"api_key": "..."}` (local; ignored by `.gitignore` `*creds.json` and `.dockerignore` `config`, both already added). Never in code, git or the image.
- The 22 existing tests pass unchanged; the sample still gives `85.3 / 100` and `5 of 10`.
- `from google import genai` only inside `ask_gemini()`: the app and tests must run without `google-genai` installed.
- Course style: typed variables, simple loops and ifs, `#` comments, `UPPER_CASE` constants.
- Verdict constants (exact strings): `AGREE = "agree"`, `BENEFIT_UNCLEAR = "benefit unclear"`, `GUESSED = "guessed"`, `MISLED = "misled"`, `SKIPPED = "skipped"`.
- Privacy line (exact copy): "This sends your listings to Google's Gemini API. Results can vary between runs. The score above does not use it."
- Tests run in the container: `docker exec nomades_python_env bash -lc 'cd ~/workspace/nomades_project && conda run -n nomades_nppd_312 python -m unittest'`
- The user makes the commits (no Co-Authored-By trailer in this repo). "Commit" steps = suggested message.
- Since 31 Oct the download report is a PDF (`pdf_report()`, fpdf2) and the JSON download is gone. The AI search results are **not** added to the PDF (out of scope, like the score).

## Review Focus

1. Gemini wraps its JSON in a ```` ```json ```` fence despite the JSON mode → `parse_answer` strips the fence and still reads it (test in Task 1).
2. The AI answers with an id that isn't in the category, or leaves one out → unknown ids ignored, missing ids = not recommended (test in Task 1).
3. Network error, bad key, 429 rate limit → `ask_gemini` raises `AISearchError`, the tab shows `st.error`, the other tabs still work (unlike the notebook, which returned the error as text) (checked by hand in Task 4 with a wrong key; the tests never call Gemini).
4. No key (no variable, no creds file) → the live button is disabled, the recorded sample run still shows (AppTest in Task 4); a creds file without `api_key` or with bad JSON → treated as no key, not a crash (unit test in Task 4).
5. An uploaded file with no category in `NEED_QUESTIONS` → `st.info("No shopper needs for the categories in this file.")`, no call made (test in Task 2: `run_search` returns `[]` without calling Gemini).

---

### Task 1: Need questions, verdicts and answer parsing

**Files:**
- Modify: `shelfready/sector.py` (after `SHOPPER_QUESTIONS`)
- Create: `shelfready/ai_search.py`
- Test: `tests/test_ai_search.py`

**Interfaces:**
- Produces: `NEED_QUESTIONS: dict[str, list[tuple]]` in `sector.py` (5 entries, values from the spec, bottle uses `capacity_ml`); in `ai_search.py`: `AISearchError(Exception)`, the 5 verdict constants, `verdict(spec_answer: str, recommended: bool) -> str`, `parse_answer(text: str, product_ids: list[str]) -> dict[str, tuple[bool, str]]`.

- [ ] **Step 0: Check the model and the key (once, in the container)**

```bash
pip install google-genai   # in nomades_nppd_312
# the user has created config/gemini_creds.json themselves; never print its content
python -c "import json; from google import genai; k = json.load(open('config/gemini_creds.json'))['api_key']; print([m.name for m in genai.Client(api_key=k).models.list() if '3.8' in m.name])"
```
Expected: a list containing `models/gemini-3.8-flash`. If the name differs, use the listed one for `AI_MODEL` and tell the user.

- [ ] **Step 1: Write the failing tests**

```python
class VerdictTests(unittest.TestCase):
    def test_benefit_unclear(self):
        self.assertEqual(verdict(YES, False), BENEFIT_UNCLEAR)

    def test_guessed_without_attribute(self):
        self.assertEqual(verdict(UNKNOWN, True), GUESSED)

class ParseTests(unittest.TestCase):
    def test_bad_answer_raises(self):
        with self.assertRaises(AISearchError):
            parse_answer("not json", ["P1"])

    def test_fenced_answer_unknown_and_missing_ids(self):
        text = '```json\n[{"id": "P1", "recommended": true, "reason": "Warm enough."}, {"id": "X9", "recommended": true, "reason": "?"}]\n```'
        picks = parse_answer(text, ["P1", "P2"])
        self.assertEqual(picks["P1"], (True, "Warm enough."))
        self.assertEqual(picks["P2"], (False, "No answer from the AI."))
        self.assertNotIn("X9", picks)
```

- [ ] **Step 2: Run, expect FAIL** (`ModuleNotFoundError: shelfready.ai_search`).

- [ ] **Step 3: Implement** `NEED_QUESTIONS` in `sector.py`, and in `ai_search.py` the constants, `AISearchError`, `verdict()` (the spec's verdict table) and `parse_answer()`: strip a leading ```` ```json ```` / trailing ```` ``` ````, `json.loads` (on `ValueError` raise `AISearchError("The AI's answer could not be read.")`), it must be a list; `recommended` counts only if it is exactly `True`; reason missing → `""`.

- [ ] **Step 4: Run the whole suite, expect 26 tests OK** (22 + 4).

- [ ] **Step 5: Commit (user):** `Add need questions, verdicts and AI answer parsing`

### Task 2: Gemini call and the search run

**Files:**
- Modify: `shelfready/ai_search.py`
- Test: `tests/test_ai_search.py`

**Interfaces:**
- Consumes: Task 1; `answer_question(product, question) -> str` and `YES/NO/UNKNOWN` from `questions.py`; `Product.attrs()`.
- Produces: `AI_MODEL: str`; `ask_gemini(prompt: str, api_key: str) -> str`; `build_prompt(question_text: str, products: list[Product]) -> str`; `rows_for_need(question: tuple, products: list[Product], answer_text: str) -> list[dict]` with keys `"need", "id", "fits", "recommended", "reason", "verdict"`; `run_search(products: list[Product], api_key: str, recorded: dict | None = None) -> list[dict]`; `record_answers(products: list[Product], api_key: str) -> dict[str, list]`; `load_recorded(path: Path) -> dict`; `CREDS_FILE: Path` (`<project>/config/gemini_creds.json`); `load_api_key(path: Path | None = None) -> str` (variable `GEMINI_API_KEY` first, else the file's `api_key` (default path `CREDS_FILE`, read at call time), else `""`; missing file, bad JSON or no `api_key` → `""`).

- [ ] **Step 1: Write the failing tests** (none of them calls Gemini)

```python
def test_rows_for_need(self):
    fits = good_product(id="T1")                                   # volume_l 30 -> fits the weekend need
    small = good_product(id="T2", attributes="volume_l: 20 | weight_g: 900 | material: nylon")
    answer = '[{"id": "T1", "recommended": false, "reason": "Not sure."}, {"id": "T2", "recommended": false, "reason": "Too small."}]'
    rows = rows_for_need(NEED_QUESTIONS["backpack"][0], [fits, small], answer)
    self.assertEqual([row["verdict"] for row in rows], [BENEFIT_UNCLEAR, SKIPPED])

def test_no_need_for_category_makes_no_call(self):
    # no key: a call to Gemini would fail, so [] proves no call was made
    self.assertEqual(run_search([good_product(category="socks")], ""), [])

def test_recorded_run_without_answer_raises(self):
    with self.assertRaises(AISearchError):
        run_search([good_product()], "", recorded={"answers": {}})

def test_load_api_key_from_file(self):
    # GEMINI_API_KEY removed from os.environ for this test (restored after)
    # temporary file {"api_key": "abc"} -> "abc"; temporary file containing "not json" -> ""
```

- [ ] **Step 2: Run, expect FAIL** (`ImportError: rows_for_need`).

- [ ] **Step 3: Implement.**
  - `build_prompt`: the spec's prompt text, one line per product: `- id: … | title: … | description: … | attributes: …` (attributes from `product.attrs()` as `key: value` joined by ` | `).
  - `rows_for_need`: `parse_answer` → one row per product with `fits = answer_question(product, question)` and `verdict(fits, recommended)`.
  - `run_search`: for each category in `NEED_QUESTIONS` (lower-case, stripped, same as `question_summary`), the products of that category; none → skip; each need question → the answer text: `recorded` given → `json.dumps(recorded["answers"][need])` (need missing → `AISearchError("No recorded answer for this question.")`), else `ask_gemini(build_prompt(...), api_key)` → `rows_for_need`.
  - `ask_gemini`: `client.models.generate_content(model=AI_MODEL, contents=prompt, config={"temperature": 0, "response_mime_type": "application/json"})`, return `response.text`; any `Exception` → `raise AISearchError(f"The AI call failed: {error}")`.
  - `load_recorded`: `json.load` of `{"recorded_on", "model", "answers": {need text: list}}`.
  - `record_answers`: same loop as `run_search` with live calls, stores `json.loads(...)` of each answer by need text.

- [ ] **Step 4: Run the whole suite, expect 30 tests OK.**

- [ ] **Step 5: Commit (user):** `Add the Gemini call and the AI search run`

### Task 3: Record the sample run and add the dependency

**Files:**
- Create: `shelfready/data/ai_search_sample.json`
- Modify: `requirements.txt`

- [ ] **Step 1:** Add `google-genai==<version installed in Step 0 of Task 1>` to `requirements.txt`.
- [ ] **Step 2:** In the container, with `config/gemini_creds.json` present, load `shelfready/data/sample_products.csv` with `load_products_from_text`, call `record_answers(products, load_api_key())`, and write `{"recorded_on": "<today, YYYY-MM-DD>", "model": AI_MODEL, "answers": ...}` with `json.dump(..., indent=2, ensure_ascii=False)`.
- [ ] **Step 3:** Check: the file has one entry per need whose category is in the sample (backpack, sleeping_bag, headlamp, bottle, stove → 5); `run_search(products, "", recorded=load_recorded(path))` runs without error. Show the user the verdicts and note any `BENEFIT_UNCLEAR` listing for the demo.
- [ ] **Step 4: Commit (user):** `Record the AI search test on the sample shop`

### Task 4: The "AI search test" tab

**Files:**
- Modify: `shelfready_app.py` (`main()` tabs, new `show_ai_search`)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `run_search`, `load_recorded`, `AISearchError`, `BENEFIT_UNCLEAR`, `load_api_key` (Task 2); `SAMPLE_FILE` and `AuditResult.source_name`.
- Produces: `show_ai_search(result: AuditResult) -> None`; constant `AI_SAMPLE_FILE: Path`.

- [ ] **Step 1: Write the failing AppTest** (same pattern as `test_sample_shop`; in `setUp`, remove `GEMINI_API_KEY` from `os.environ` and point `shelfready.ai_search.CREDS_FILE` at a path that does not exist, restoring both in `tearDown`)

```python
def test_ai_tab_replays_recorded_run_without_key(self):
    app = AppTest.from_file(str(APP_FILE)).run(timeout=APP_TIMEOUT)
    app.checkbox[0].check().run(timeout=APP_TIMEOUT)
    self.assertEqual(len(app.exception), 0)
    live = [b for b in app.button if b.label == "Run with live AI"][0]
    self.assertTrue(live.disabled)
    self.assertTrue(any("Recorded run" in c.value for c in app.caption))
```

- [ ] **Step 2: Run, expect FAIL** (no such button).

- [ ] **Step 3: Implement `show_ai_search`.** Order on the tab: one-sentence explanation of the test, the privacy line (exact copy), the button `"Run with live AI"` (`disabled` when `load_api_key() == ""`, with `st.caption("No Gemini key: set GEMINI_API_KEY or config/gemini_creds.json to run the live test.")`). Answers: live (`run_search(products, load_api_key())`) when the button was pressed, else the recorded run (`run_search(products, "", recorded=load_recorded(AI_SAMPLE_FILE))`) when `result.source_name == SAMPLE_FILE.name` (caption `f"Recorded run, {recorded['recorded_on']}"`), else stop after the button. Rows `[]` → `st.info("No shopper needs for the categories in this file.")`. Show `st.metric("Benefit unclear", f"{x} of {y} listings")` (y = rows whose `fits` is `YES`) and a dataframe with columns Shopper need · Listing · Specs fit · AI recommends · AI's reason · Verdict. `AISearchError` → `st.error(str(error))`. Add the tab to `st.tabs([... , "AI search test"])` after "Shopper questions".

- [ ] **Step 4: Run the whole suite, expect 31 tests OK, and `test_sample_shop` still 85.3 / 5 of 10.** Then `streamlit run shelfready_app.py` in the container and press "Run with live AI" once on the sample with the key set.

- [ ] **Step 5: Commit (user):** `Add the AI search test tab`

### Task 5: Deploy and make the notes agree

**Files:**
- Modify: `README.md` (the user has uncommitted edits in it: add lines, don't rewrite)

- [ ] **Step 1:** README: one short section "AI search test (optional)": what it does, that it sends listings to Gemini only when the button is pressed, that it is not in the score, `GEMINI_API_KEY`. Change any "no AI" claim to "the score uses no AI".
- [ ] **Step 2:** Render dashboard: add the environment variable `GEMINI_API_KEY` (the user does this). Push to `origin`, then to `render` with the `commit-tree` command from the notes. Check the live site: sample → AI tab shows the recorded run.
- [ ] **Step 3:** Notion, so nothing contradicts: Teacher Review Prep §1 pitch, §2 demo (add the AI tab step), §3 build ("standard library only" → plus the optional `google-genai`), §9 limits, §11 main principle, §13 privacy (data goes to Google only on the button), §14 (built); "After the MVP" to-do ticked; scan the project page, "How the AI check works", the Deep Dive and the Claude doc "ShelfReady and GEO" for "no AI" claims; check the deck `ShelfReady.pptx`. Same pages: "HTML report" / "JSON" → "PDF report" (changed 31 Oct); in Teacher Review Prep §13 and the "why no database" answer, the stored summary was described as "almost `json_report()`", which no longer exists.
- [ ] **Step 4: Commit (user):** `Document the AI search test`
