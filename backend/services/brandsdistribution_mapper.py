"""Brandsdistribution catalogue mapping for LUMIÈRE.

The mapper is deliberately pure and network-free so it can be tested against
Brandsdistribution sample/export rows before any paid or authenticated API is
enabled. It never invents missing URLs, prices, stock, colours or images.
"""
from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse

PROVIDER_ID = "brandsdistribution"


def _first(row: dict, *keys: str):
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _http_url(value) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    parsed = urlparse(text)
    return text if parsed.scheme in ("http", "https") and parsed.netloc else None


def _number(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def _quantity(value) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def map_export_row(row: dict, product_page_url: str | None = None) -> dict:
    """Map one PRODUCT export row to LUMIÈRE's provider-neutral raw contract.

    Brandsdistribution's documented exports separate PRODUCT and MODEL rows.
    MODEL rows (size/variant stock) should be aggregated separately before a
    production adapter is enabled.
    """
    record_type = str(_first(row, "record_type", "recordType") or "PRODUCT").upper()
    if record_type != "PRODUCT":
        raise ValueError("Expected a Brandsdistribution PRODUCT row")

    external_id = _first(row, "product_id", "productId", "code")
    name = _first(row, "name", "productname", "product_name")
    source_url = _http_url(product_page_url or _first(row, "source_url", "url", "product_url"))
    if not external_id or not name:
        raise ValueError("Brandsdistribution row is missing product_id or name")
    if not source_url:
        raise ValueError("A verified Brandsdistribution product page URL is required")

    colour = _first(row, "color", "colour")
    image = _http_url(_first(row, "picture 1", "picture_1", "picture1", "image_url"))
    price = _number(_first(row, "street_price", "streetPrice", "suggested_price", "suggestedPrice"))
    quantity = _quantity(_first(row, "product_quantity", "availability", "quantity"))

    category = _first(row, "category", "Categorie", "categorie")
    subcategory = _first(row, "subcategory", "Sottocategorie", "sottocategorie")
    if category and subcategory:
        category = f"{category} / {subcategory}"

    return {
        "external_id": str(external_id),
        "name": str(name),
        "brand": _first(row, "brand", "Brand"),
        "category": category,
        "description": str(_first(row, "plain_description", "description") or ""),
        "price": price,
        "currency": "EUR" if price is not None else None,
        "image_url": image,
        "source_url": source_url,
        "colour_names": [str(colour)] if colour else [],
        "sizes": [],
        "materials": [],
        "occasions": [],
        "palette_tags": [],
        "availability": str(quantity) if quantity is not None else None,
    }


def aggregate_model_rows(product: dict, model_rows: Iterable[dict]) -> dict:
    """Attach source-backed sizes and summed variant availability to a product."""
    sizes: list[str] = []
    total = 0
    saw_quantity = False
    for row in model_rows:
        if str(_first(row, "record_type", "recordType") or "").upper() != "MODEL":
            continue
        size = _first(row, "model_size", "size")
        if size and str(size) not in sizes:
            sizes.append(str(size))
        qty = _quantity(_first(row, "model_quantity", "availability", "quantity"))
        if qty is not None:
            total += qty
            saw_quantity = True
    result = dict(product)
    result["sizes"] = sizes
    if saw_quantity:
        result["availability"] = str(total)
    return result
