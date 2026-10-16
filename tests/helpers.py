from shelfready.models import Product


def good_product(**changes):
    """A listing that passes every rule. Pass keyword arguments to break one field."""
    values = dict(
        id="T1",
        category="backpack",
        title="Trail daypack 30 l",
        description="Hiking daypack with a rain cover and a padded back panel. The main compartment holds 30 l and the pack weighs 900 g.",
        price=89.0,
        currency="EUR",
        availability="in_stock",
        gtin="4006381333931",
        brand="TestBrand",
        image_url="https://example.com/a.jpg",
        attributes="volume_l: 30 | weight_g: 900 | material: nylon",
    )
    values.update(changes)
    return Product(**values)
