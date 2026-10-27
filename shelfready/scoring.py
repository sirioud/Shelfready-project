# Runs every rule on each product and adds up the points.

from .models import Product, RuleResult
from .questions import unanswered_questions
from .rules import ALL_RULES

PASS_SCORE: int = 90 # minimum score (out of 100) for a listing to count as "likely to be recommended"

# if one of these rules fails, the listing is not ready whatever its score
# feed_standard: google merchant center would reject the listing (no title, no price, wrong availability...)
BLOCKING_RULES: list[str] = ["feed_standard"]


class ProductScore:
    def __init__(self, product: Product, score: int, results: list[RuleResult]):
        self.product: Product = product
        self.score: int = score
        self.results: list[RuleResult] = results

        # the rules this product did not pass
        self.failed: list[RuleResult] = []
        for result in results:
            if not result.passed:
                self.failed.append(result)

        # blocked = fails a rule that makes the feed reject the listing
        self.blocked: bool = False
        for result in self.failed:
            if result.rule in BLOCKING_RULES:
                self.blocked = True

        self.is_ready: bool = score >= PASS_SCORE and not self.blocked

    def to_dict(self) -> dict:
        # for the json download
        failed_rules: list[dict] = []
        for result in self.failed:
            failed_rules.append({"rule": result.rule, "message": result.message})

        return {
            "id": self.product.id,
            "title": self.product.title,
            "category": self.product.category,
            "score": self.score,
            "ready": self.is_ready,
            "blocked": self.blocked,
            "failed": failed_rules,
            "cannot_be_matched": unanswered_questions(self.product),
        }


def score_product(product: Product) -> ProductScore:
    results: list[RuleResult] = []
    total: int = 0
    for rule in ALL_RULES:
        result: RuleResult = rule(product)
        results.append(result)
        total = total + result.points
    return ProductScore(product, total, results)


def score_catalog(products: list[Product]) -> tuple[list[ProductScore], float]:
    # returns every product score and the average for the whole catalog
    scores: list[ProductScore] = []
    for product in products:
        scores.append(score_product(product))

    if len(scores) == 0:
        return scores, 0.0

    total: int = 0
    for product_score in scores:
        total = total + product_score.score
    average: float = total / len(scores)
    return scores, round(average, 1)


def count_ready(scores: list[ProductScore]) -> int:
    ready: int = 0
    for product_score in scores:
        if product_score.is_ready:
            ready = ready + 1
    return ready


def count_unanswered(scores: list[ProductScore]) -> int:
    # shopper questions that cannot be matched, for the whole catalog
    total: int = 0
    for product_score in scores:
        total = total + len(unanswered_questions(product_score.product))
    return total


def most_common_problems(scores: list[ProductScore], limit: int = 3) -> list[tuple[str, int]]:
    # the rules that failed most often, e.g. [("gtin", 4), ("units", 2)]
    counts: dict[str, int] = {}
    for product_score in scores:
        for result in product_score.failed:
            if result.rule in counts:
                counts[result.rule] = counts[result.rule] + 1
            else:
                counts[result.rule] = 1

    # take the biggest count, then the next one, until we have "limit" problems
    problems: list[tuple[str, int]] = []
    while len(problems) < limit and len(counts) > 0:
        best_rule: str = ""
        best_count: int = 0
        for rule in counts:
            if counts[rule] > best_count:
                best_rule = rule
                best_count = counts[rule]
        problems.append((best_rule, best_count))
        del counts[best_rule]
    return problems
