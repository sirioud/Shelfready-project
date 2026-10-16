# Real shop exports vs the ShelfReady CSV

Reference note for `sample_products.csv`. Why the sample file looks the way it
does, and how it relates to what a real shop would hand you.

## What a Shopify export looks like

`products_export.csv`, first columns of a ~50-column file:

```
Handle,Title,Body (HTML),Vendor,Product Category,Type,Tags,Published,Option1 Name,Option1 Value,Variant SKU,Variant Grams,Variant Inventory Qty,Variant Price,Variant Barcode,Image Src,Status
trail-daypack-30l,Trail Daypack 30L,"<p>Hiking daypack with a padded laptop sleeve.</p>",Nordwear,Apparel & Accessories > Handbags,Backpack,"hiking,outdoor",TRUE,Size,One Size,NW-TD30-BLK,900,14,89.00,4006381333931,https://cdn.shopify.com/s/files/1/0/trail.jpg,active
```

Every variant carries a SKU, a price, a title and a Barcode field holding the
UPC, EAN or ISBN.

## What a Google Merchant Center feed looks like

The feed that actually reaches shopping engines:

```
id, title, description, link, image_link, availability, price, brand, gtin, mpn, condition, product_type, google_product_category
```

Plus optional attributes: `material`, `color`, `size`, `pattern`, `age_group`.

## How ShelfReady maps onto them

| ShelfReady   | Shopify         | Merchant Center |
| ------------ | --------------- | --------------- |
| `id`         | Variant SKU     | `id`            |
| `category`   | Type            | `product_type`  |
| `title`      | Title           | `title`         |
| `description`| Body (HTML)     | `description`   |
| `price`      | Variant Price   | `price`         |
| `currency`   | (shop setting)  | in `price`      |
| `availability`| Status         | `availability`  |
| `gtin`       | Variant Barcode | `gtin`          |
| `brand`      | Vendor          | `brand`         |
| `image_url`  | Image Src       | `image_link`    |
| `attributes` | —               | — (partly)      |

## Three differences that are deliberate

**Eleven columns instead of fifty.** A real export carries inventory counts,
tax settings, SEO fields, collection membership. None of it affects whether an
AI assistant can understand the listing. The sample keeps only what the rules
read.

**Plain text instead of HTML.** `Body (HTML)` contains markup and commas, so
real values are quoted. The sample avoids commas entirely to keep the CSV
readable while learning. Real input would need the HTML stripped before the
rules run.

**The `attributes` column does not exist anywhere.** This is the important one.
Shopify gives three free-text options (typically Size, Colour, Material).
Merchant Center has a fixed handful of attributes. Everything else — volume in
litres, lumens, runtime hours, temperature ratings, weight — ends up inside the
description text.

That gap is what the `structured_share` rule measures. A spec written as
`lumens_lm: 400` can be read reliably by an assistant comparing headlamps; the
same fact inside "bright headlamp with 400 lm output" can only sometimes be
extracted. The platforms have no field for it, so most shops write it in prose,
and most listings lose out.

## Consequence for the project

If ShelfReady were pointed at a real export, one mapping step would come first:
rename the columns, strip the HTML, and fold whatever structured options exist
(Size, Colour, Material) into the `attributes` field. The eleven rules would then
run unchanged.

Worth stating in the presentation: the tool reads a normalised format on
purpose, so the scoring logic stays independent of any one platform's export
quirks.
