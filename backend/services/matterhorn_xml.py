"""Matterhorn XML catalogue adapter for LUMIÈRE.

Maps source-backed Matterhorn <product> records to LUMIÈRE's normalized raw
catalogue contract. Supplier identity and wholesale metadata remain backend-only.
"""
from __future__ import annotations

import re
from html import unescape
from xml.etree import ElementTree as ET

PROVIDER_ID = "matterhorn"
_PRODUCT_URL_BASE = "https://matterhorn-wholesale.com/product/"

_TAG_RE = re.compile(r"<[^>]+>")
_MATERIAL_RE = re.compile(r"<strong>\s*([^<]+?)\s*</strong>\s*([0-9]+(?:[.,][0-9]+)?)\s*%", re.I)


def _text(node: ET.Element | None, default: str = "") -> str:
    return (node.text or "").strip() if node is not None else default


def _clean_description(value: str) -> str:
    # Description CDATA contains product prose plus HTML composition/size tables.
    # Keep readable prose; structured sizes and stock come from <options>.
    head = value.split("<div class='prod_data'>", 1)[0]
    return " ".join(unescape(_TAG_RE.sub(" ", head)).split())


def _materials(value: str) -> list[str]:
    return [
        f"{name.strip()} {amount.replace(',', '.')}%"
        for name, amount in _MATERIAL_RE.findall(value or "")
    ]


def map_product_element(product: ET.Element) -> dict:
    """Map one genuine Matterhorn XML product without inventing commerce data."""
    external_id = (product.get("id") or "").strip()
    name = _text(product.find("name"))
    if not external_id or not name:
        raise ValueError("Matterhorn product is missing id or name")

    description_html = _text(product.find("description"))
    images = [
        _text(image)
        for image in product.findall("./images/image_url")
        if _text(image).startswith(("http://", "https://"))
    ]

    sizes: list[str] = []
    total_stock = 0
    variants: list[dict] = []
    for option in product.findall("./options/option"):
        size = _text(option.find("option_name"))
        stock_text = _text(option.find("STOCK"), "0")
        try:
            stock = max(0, int(float(stock_text)))
        except ValueError:
            stock = 0
        if size and size.upper() not in [item.upper() for item in sizes]:
            sizes.append(size)
        total_stock += stock
        variants.append({
            "external_id": option.get("id"),
            "size": size or None,
            "stock": stock,
            "ean": _text(option.find("ean")) or None,
        })

    price_text = _text(product.find("price"))
    try:
        price = float(price_text) if price_text else None
    except ValueError:
        price = None

    colour = _text(product.find("color"))
    category = _text(product.find("category"))
    category_path = _text(product.find("category_path"))
    garment_type = _text(product.find("type"))

    return {
        "external_id": external_id,
        "name": name,
        "brand": _text(product.find("brand")) or None,
        "category": category or garment_type or None,
        "description": _clean_description(description_html),
        "price": price,
        "currency": "AUD",
        "image_url": images[0] if images else None,
        "source_url": f"{_PRODUCT_URL_BASE}{external_id}",
        "colour_names": [colour] if colour else [],
        "sizes": sizes,
        "materials": _materials(description_html),
        "occasions": [],
        "palette_tags": [],
        "availability": str(total_stock),
        # Private adapter metadata: never expose through customer_product_view.
        "_matterhorn": {
            "category_path": category_path or None,
            "type": garment_type or None,
            "images": images,
            "variants": variants,
        },
    }


def iter_products(xml_path: str):
    """Stream a large Matterhorn XML file without loading it all into memory.

    ElementTree is strict: malformed XML raises ParseError. Callers importing a
    supplier feed should log the byte/line error and retain products yielded
    before that point rather than presenting unparsed records as valid.
    """
    context = ET.iterparse(xml_path, events=("end",))
    for _event, elem in context:
        if elem.tag == "product":
            yield map_product_element(elem)
            elem.clear()
