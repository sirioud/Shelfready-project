# AI search test: a shopper describes a need to an AI assistant (Gemini), the AI picks products,
# and its picks are compared with what the specs prove (questions.py: yes / no / unknown).
# When the specs say a product fits but the AI does not recommend it, the listing does not make its use clear.
# Not part of the score.

import json
import os
from pathlib import Path

from .models import Product
from .questions import NO, UNKNOWN, YES, answer_question
from .sector import NEED_QUESTIONS

AI_MODEL: str = "gemini-3.5-flash" # 3.8 was overloaded (503) on 2-3 Nov; 3.5 answers reliably
AI_TIMEOUT_SECONDS: int = 60 # after this the call gives up, so the page never hangs
# the key: the variable GEMINI_API_KEY on Render, or this file on your own computer (never in git, see .gitignore)
CREDS_FILE: Path = Path(__file__).parent.parent / "config" / "gemini_creds.json"

# the five verdicts, one per row of the comparison table
AGREE: str = "agree"                      # specs yes, AI yes: the AI found it
BENEFIT_UNCLEAR: str = "benefit unclear"  # specs yes, AI no: it fits, but the text does not say what it is for
GUESSED: str = "guessed"                  # specs unknown, AI yes: recommended without the spec
MISLED: str = "misled"                    # specs no, AI yes: the text suggests a use the specs do not support
SKIPPED: str = "skipped"                  # specs no or unknown, AI no: correctly not recommended


class AISearchError(Exception):
    # the AI call failed or its answer cannot be read. shown as a clean message, like LoaderError
    pass


def verdict(spec_answer: str, recommended: bool) -> str:
    # spec_answer is YES, NO or UNKNOWN from answer_question()
    if spec_answer == YES and recommended:
        return AGREE
    if spec_answer == YES:
        return BENEFIT_UNCLEAR
    if spec_answer == UNKNOWN and recommended:
        return GUESSED
    if spec_answer == NO and recommended:
        return MISLED
    return SKIPPED


def strip_fence(text: str) -> str:
    # Gemini sometimes wraps the JSON in ```json ... ``` even when asked for JSON only
    cleaned: str = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()
    return cleaned


def parse_answer(text: str, product_ids: list[str]) -> dict[str, tuple[bool, str]]:
    # the AI answers with a JSON list: [{"id": "P1", "recommended": true, "reason": "..."}, ...]
    # returns {id: (recommended, reason)} for every id asked about, and only for those
    try:
        answer = json.loads(strip_fence(text))
    except ValueError:
        raise AISearchError("The AI's answer could not be read.")
    if not isinstance(answer, list):
        raise AISearchError("The AI's answer could not be read.")

    # an id the AI left out counts as not recommended
    picks: dict[str, tuple[bool, str]] = {}
    for product_id in product_ids:
        picks[product_id] = (False, "No answer from the AI.")

    for item in answer:
        if not isinstance(item, dict):
            continue
        product_id = item.get("id")
        if product_id not in picks: # an id that was not asked about is ignored
            continue
        recommended: bool = item.get("recommended") is True # "yes" or 1 do not count, only true
        reason = item.get("reason", "")
        if not isinstance(reason, str):
            reason = ""
        picks[product_id] = (recommended, reason)
    return picks


def load_api_key(path: Path | None = None) -> str:
    # the variable GEMINI_API_KEY first (Render), else the api_key in the creds file, else "" (no key)
    key: str = os.environ.get("GEMINI_API_KEY", "")
    if key != "":
        return key
    if path is None:
        path = CREDS_FILE
    try:
        with open(path, encoding="utf-8") as file:
            creds = json.load(file)
    except (OSError, ValueError): # no file, or not json
        return ""
    if not isinstance(creds, dict):
        return ""
    key = creds.get("api_key", "")
    if not isinstance(key, str):
        return ""
    return key


def ask_gemini(prompt: str, api_key: str) -> str:
    # sends the prompt to Gemini and returns its answer as text
    try:
        # imported here, so the rest of the app and the tests work without google-genai installed
        from google import genai
        # kept in a variable: otherwise the client is closed before the call. the timeout is in milliseconds
        client = genai.Client(api_key=api_key, http_options={"timeout": AI_TIMEOUT_SECONDS * 1000})
        response = client.models.generate_content(
            model=AI_MODEL,
            contents=prompt,
            config={"temperature": 0, "response_mime_type": "application/json"},
        )
        return response.text
    except Exception as error: # no network, wrong key, too many requests (429)...
        raise AISearchError(f"The AI call failed: {error}")


def build_prompt(question_text: str, products: list[Product]) -> str:
    # the shopper's need, then one line per product with everything the listing says
    lines: list[str] = []
    lines.append(f'You are an AI shopping assistant. A shopper asks: "{question_text}".')
    lines.append("These are the products the shop sells in this category:")
    for product in products:
        specs: list[str] = []
        for key, value in product.attrs().items():
            specs.append(f"{key}: {value}")
        lines.append(f"- id: {product.id} | title: {product.title} | description: {product.description} | attributes: {' | '.join(specs)}")
    lines.append("For each product, decide whether you would recommend it for this request, using only the information given.")
    lines.append('Answer with JSON only: a list of {"id": "...", "recommended": true or false, "reason": "one short sentence"}.')
    return "\n".join(lines)


def rows_for_need(question: tuple, products: list[Product], answer_text: str) -> list[dict]:
    # one row per product: what the specs say, what the AI said, and the verdict
    product_ids: list[str] = []
    for product in products:
        product_ids.append(product.id)
    picks: dict[str, tuple[bool, str]] = parse_answer(answer_text, product_ids)

    rows: list[dict] = []
    for product in products:
        fits: str = answer_question(product, question)
        recommended: bool = picks[product.id][0]
        reason: str = picks[product.id][1]
        rows.append({
            "need": question[0],
            "id": product.id,
            "fits": fits,
            "recommended": recommended,
            "reason": reason,
            "verdict": verdict(fits, recommended),
        })
    return rows


def products_by_need(products: list[Product]) -> list[tuple[tuple, list[Product]]]:
    # each need question with the products of its category, skipping categories not in the file
    pairs: list[tuple[tuple, list[Product]]] = []
    for category in NEED_QUESTIONS:
        in_category: list[Product] = []
        for product in products:
            if product.category.strip().lower() == category:
                in_category.append(product)
        if len(in_category) == 0:
            continue
        for question in NEED_QUESTIONS[category]:
            pairs.append((question, in_category))
    return pairs


def run_search(products: list[Product], api_key: str, recorded: dict | None = None) -> list[dict]:
    # one answer per need: from Gemini, or from the recorded run when recorded is given
    rows: list[dict] = []
    for question, in_category in products_by_need(products):
        need: str = question[0]
        if recorded is not None:
            if need not in recorded["answers"]:
                raise AISearchError("No recorded answer for this question.")
            answer_text: str = json.dumps(recorded["answers"][need])
        else:
            answer_text = ask_gemini(build_prompt(need, in_category), api_key)
        rows = rows + rows_for_need(question, in_category, answer_text)
    return rows


def record_answers(products: list[Product], api_key: str) -> dict[str, list]:
    # asks Gemini every need once and keeps the answers, to save them as the recorded run
    answers: dict[str, list] = {}
    for question, in_category in products_by_need(products):
        need: str = question[0]
        answer_text: str = ask_gemini(build_prompt(need, in_category), api_key)
        parse_answer(answer_text, []) # raises AISearchError if the answer cannot be read
        answers[need] = json.loads(strip_fence(answer_text))
    return answers


def load_recorded(path: Path) -> dict:
    # the recorded run: {"recorded_on": "...", "model": "...", "answers": {need: [...]}}
    with open(path, encoding="utf-8") as file:
        return json.load(file)
