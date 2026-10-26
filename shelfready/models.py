#Data model for ShelfReady.
#Product = one row of the shop's csv file
#RuleResult = the result of one check on one product

from .attributes import parse_attributes


class Product:
    # id has no default -> a product cannot exist without an id, other values can be empty cells
    def __init__(
        self,
        id: str,
        category: str = "",
        title: str = "",
        description: str = "",
        price: float | None = None,
        currency: str = "",
        availability: str = "",
        gtin: str = "", # barcode (global trade item number), kept as text not int so leading zeros stay
        brand: str = "",
        image_url: str = "",
        attributes: str = "", # key: value pairs separated by | e.g. "volume_l: 30 | material: nylon"
    ):
        self.id: str = id
        self.category: str = category
        self.title: str = title
        self.description: str = description
        self.price: float | None = price
        self.currency: str = currency
        self.availability: str = availability
        self.gtin: str = gtin
        self.brand: str = brand
        self.image_url: str = image_url
        self.attributes: str = attributes
        self._parsed: dict[str, str] | None = None # cache for attrs(), filled on first use

    def attrs(self) -> dict[str, str]:
        # the attributes column parsed into {key: value}, computed once and reused
        # almost every rule needs this, so parsing it one time per product avoids the repeated work
        if self._parsed is None:
            self._parsed = parse_attributes(self.attributes)
        return self._parsed

    def text(self) -> str:
        # title and description together, the free text most rules scan
        return self.title + " " + self.description

    def __repr__(self) -> str:
        return f"Product(id='{self.id}', category='{self.category}', title='{self.title}')"

#TODO: add a __str__() that prints all fields, for debugging and check functions

class RuleResult:
    def __init__(self, rule: str, passed: bool, points: int, message: str = ""):
        self.rule: str = rule
        self.passed: bool = passed
        self.points: int = points
        self.message: str = message # what to fix, empty if the rule passed

    def __repr__(self) -> str:
        return f"RuleResult(rule='{self.rule}', passed={self.passed}, points={self.points})"


