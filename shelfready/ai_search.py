# AI search test: a shopper describes a need to an AI assistant (Gemini), the AI picks products,
# and its picks are compared with what the specs prove (questions.py: yes / no / unknown).
# When the specs say a product fits but the AI does not recommend it, the listing does not make its use clear.
# Not part of the score.

import json

from .questions import NO, UNKNOWN, YES

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


def parse_answer(text: str, product_ids: list[str]) -> dict[str, tuple[bool, str]]:
    # the AI answers with a JSON list: [{"id": "P1", "recommended": true, "reason": "..."}, ...]
    # returns {id: (recommended, reason)} for every id asked about, and only for those
    cleaned: str = text.strip()
    # Gemini sometimes wraps the JSON in ```json ... ``` even when asked for JSON only
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()

    try:
        answer = json.loads(cleaned)
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
