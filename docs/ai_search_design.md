# AI search test (benefit clarity) — design

Status: built 1–3 Nov 2026 (tab "AI search test", recorded run on the sample, 31 tests). Written 30 Oct 2026, for the presentation on 4 Nov.

## Why

The teacher's fifth idea, **benefit clarity**: does a listing say what the product is *for* and *for whom*, not only what it is?
"400 lm" is a characteristic; "lights a trail at running pace" is a benefit.
Judging that is a question of meaning, so the 14 rules can't do it. The teacher named this as the place where an AI may enter the tool:
an AI judges how another AI will read a listing.

The AI search test simulates a shopper asking an AI assistant for a **need** ("a headlamp for night trail running"),
and compares the assistant's picks with what ShelfReady already knows from the specs (`questions.py`: yes / no / unknown).
When the specs say a product qualifies but the AI does not recommend it, the listing does not make its use clear.

## What does not change

- The 14 rules, the 100 points, `PASS_SCORE`, the "ready" count, the sample's **85.3 / 5 of 10**, and the 22 existing tests.
- The AI test is a separate module and a separate tab. It is never part of the score.
- Nothing is saved on the server.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Provider | Google Gemini via `google-genai` (the SDK from lesson 47) | The user has a Gemini API key. Gemini only: no provider classes (decided 1 Nov), one plain function calls it |
| Model | constant `AI_MODEL = "gemini-3.5-flash"` | First choice was `gemini-3.8-flash` (the lesson 47 model), but it answered 503 "high demand" on 2 and 3 Nov 2026; 3.5 Flash answered reliably, so it is used for the recorded run and the live button |
| What the AI sees | the full listing: title, description, attributes | Realistic (an assistant gets the feed data). If it still misses a qualifying product with all the data, that is a stronger finding |
| Calls | one call per need question, with all the products of that category | Simple loop, easy to explain; about 6 calls per run, under the free-tier limit |
| Answer format | JSON only (`response_mime_type="application/json"`), `temperature=0` | Machine-readable, as stable as the API allows |
| Demo | the sample shop replays a **recorded run** saved in `shelfready/data/` | A 429 rate limit or no network cannot break the demo |
| Key | environment variable `GEMINI_API_KEY` on Render; locally `config/gemini_creds.json` (`{"api_key": "..."}`), ignored by git (`*creds.json`) and Docker (`config`) | Same pattern as `creds.json` in the course repo. Never in git, never in the image, never in the code (unlike the course notebook) |

## Data: need questions in `sector.py`

A new dict `NEED_QUESTIONS`, one question per category, reusing the shape of `SHOPPER_QUESTIONS`
(text, attribute, test, wanted value), so `answer_question()` works on it unchanged:

```python
NEED_QUESTIONS: dict[str, list[tuple]] = {
    "backpack": [("A backpack for a weekend hut-to-hut hike", "volume_l", "at_least", 30)],
    "sleeping_bag": [("A sleeping bag for a winter night in the Alps", "limit_c", "at_most", -5)],
    "headlamp": [("A headlamp for night trail running", "lumens_lm", "at_least", 300)],
    "bottle": [("A bottle with enough water for a long day hike", "capacity_ml", "at_least", 750)],
    "stove": [("A stove for ultralight trekking", "weight_g", "at_most", 100)],
}
```

The text is a need (what the shopper wants to do); the attribute/test/value is the spec that proves a product fits it.
Exact wordings and values are checked against `SHOPPER_QUESTIONS` and the sample when building.

## Module: `shelfready/ai_search.py`

Gemini only, so no provider classes (decided 1 Nov 2026): one plain function calls Gemini, and the recorded run is just saved Gemini answers.

- `AISearchError(Exception)`: the AI call failed or its answer can't be read. Shown as a clean message, like `LoaderError`.

Functions:

- `ask_gemini(prompt, api_key) -> str`: `genai.Client(api_key=...)`, `client.models.generate_content(model=AI_MODEL, contents=prompt, config={...})`, returns the answer text.
  `from google import genai` is imported inside the function, so the rest of the app and the tests run without the package.
- `build_prompt(question_text, products) -> str`
- `parse_answer(text, product_ids) -> dict[str, tuple[bool, str]]`: `json.loads`, keeps only known ids,
  a missing id counts as not recommended; raises `AISearchError` on bad JSON.
- `verdict(spec_answer, recommended) -> str`: the table below.
- `rows_for_need(question, products, answer_text) -> list[dict]`: one row per product: need, id, spec answer, recommended, AI reason, verdict. No network: this is what the tests check.
- `run_search(products, api_key, recorded=None) -> list[dict]`: for each category in the file that has a need question, gets one answer
  (from Gemini, or from the recorded run when `recorded` is given) and returns the rows of `rows_for_need`.
- `load_recorded(path) -> dict`: reads `shelfready/data/ai_search_sample.json`.

Prompt (English, short):

```
You are an AI shopping assistant. A shopper asks: "<need>".
These are the products the shop sells in this category:
- id: P002 | title: ... | description: ... | attributes: limit_c: -8 | weight_g: 1200
For each product, decide whether you would recommend it for this request, using only the information given.
Answer with JSON only: a list of {"id": "...", "recommended": true or false, "reason": "one short sentence"}.
```

## Verdicts

| Specs (`answer_question`) | AI recommends? | Verdict | Message to the shop owner |
|---|---|---|---|
| yes | yes | `AGREE` | The AI found it |
| yes | no | `BENEFIT_UNCLEAR` | It fits, but the AI didn't see it: say what it's for and for whom |
| unknown | yes | `GUESSED` | The AI recommended it without the spec: add the attribute |
| no | yes | `MISLED` | The text suggests a use the specs don't support |
| no / unknown | no | `SKIPPED` | Correctly not recommended |

## Web page: tab "AI search test"

- New fifth tab after "Shopper questions". Off until opened; nothing is sent before a button is pressed.
- Text above the button: "This sends your listings to Google's Gemini API. Results can vary between runs. The score above does not use it."
- Sample shop: shows the recorded run, labelled "Recorded run, <date>". Button "Run with live AI" when a key is set.
- Uploaded file: button "Run with live AI". No key (neither the variable nor the creds file): the button is disabled with "No Gemini key: set GEMINI_API_KEY or config/gemini_creds.json to run the live test."
- Result: a count ("Benefit unclear: x of y listings") and a table: Shopper need · Listing · Specs fit · AI recommends · AI's reason · Verdict.
- `AISearchError` → `st.error(...)` with the message, the rest of the page still works.

## Tests: `tests/test_ai_search.py` (no network)

1. `test_benefit_unclear`: specs yes + AI no → `BENEFIT_UNCLEAR`.
2. `test_guessed_without_attribute`: specs unknown + AI yes → `GUESSED`.
3. `test_bad_answer_raises`: `parse_answer("not json", ...)` → `AISearchError`.
4. `test_rows_for_need`: a fixed answer text; `rows_for_need` on `good_product(...)` listings gives the expected rows.

The existing 22 tests stay unchanged and must still pass; the sample must still give 85.3 / 5 of 10.

## Setup

- `requirements.txt`: add `google-genai` (pinned). Course env: `pip install google-genai` in `nomades_nppd_312`.
- Render: add the `GEMINI_API_KEY` environment variable in the dashboard. Dockerfile unchanged.
- Recorded run: one live run on the sample, answers saved to `shelfready/data/ai_search_sample.json` and committed.

## Docs and notes to update (so nothing contradicts)

- README: "no AI" → "the score uses no AI; an optional AI search test sends listings to Gemini when you press its button".
- Notion "After the MVP": benefit clarity is being built as the AI search test; the keyword-hint weekend to-do is replaced.
- Notion "Teacher Review Prep": §1 pitch, §2 demo, §3 build, §9 limits, §11 main principle, §13 persistence/privacy, §14 benefit clarity.
- Every other ShelfReady page (project page, "How the AI check works", Deep Dive) and the Claude doc "ShelfReady and GEO": scan for "no AI" claims.
- Presentation deck (`ShelfReady.pptx`): check for "no AI" wording.

## Limits to say openly

- A simulation with one model, not real AI Mode (Wen et al., ICML 2026: offline results are only weakly linked to real visibility).
- Answers can vary between runs; the recorded run is one sample.
- Turning it on sends the listings to Google.
- "Benefit unclear" is a signal for the owner, not proof: the AI can also be wrong.

## Out of scope

- Scoring benefit clarity in the 100 points.
- Any AI other than Gemini (decided 1 Nov 2026).
- Rewriting descriptions with AI.
