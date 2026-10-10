"""Import genuine Matterhorn productsAUD.xml into a local, source-backed JSON snapshot.

Usage: python scripts/import_matterhorn_xml.py /path/to/productsAUD.xml
Never commit supplier feed, generated JSON or API credentials.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / ".lumiere-private-catalogue" / "matterhorn_products.json"


def field(element, name):
    node = element.find(name)
    return (node.text or "").strip() if node is not None else ""


def nested_values(element, tag):
    return [(node.text or "").strip() for node in element.iter(tag) if (node.text or "").strip()]


def parse_product(element):
    identifier = element.attrib.get("id") or field(element, "id")
    name = field(element, "name")
    colour = field(element, "color")
    price_text = field(element, "price").replace(",", ".")
    category_path = field(element, "category_path")
    if not (identifier and name and colour and price_text):
        return None
    try:
        price = float(price_text)
    except ValueError:
        return None
    if price < 0:
        return None
    images = nested_values(element, "image_url")
    if not images or not images[0].startswith(("https://", "http://")):
        return None
    sizes = list(dict.fromkeys(nested_values(element, "option_name")))
    stock_values = nested_values(element, "STOCK")
    quantity = 0
    for value in stock_values:
        try:
            quantity += max(0, int(float(value)))
        except ValueError:
            continue
    # A missing stock field is unknown, not zero.
    availability = str(quantity) if stock_values else None
    return {
        "external_id": identifier,
        "name": name,
        "brand": field(element, "brand"),
        "category": field(element, "type"),
        "category_path": category_path,
        "description": field(element, "description"),
        "price": price,
        "currency": "AUD",
        "image_url": images[0],
        "source_url": None,
        "colour_names": [colour],
        "sizes": sizes,
        "materials": [],
        "occasions": [],
        "palette_tags": [],
        "availability": availability,
    }


class SanitizedXML:
    """Filter XML-forbidden control bytes in supplier exports while streaming."""
    def __init__(self, path):
        self.handle = open(path, "rb")

    def read(self, size=-1):
        chunk = self.handle.read(size)
        return chunk.translate(None, bytes(list(range(0, 9)) + [11, 12] + list(range(14, 32))))

    def close(self):
        self.handle.close()


def import_xml(source, destination=OUTPUT):
    products = {}
    # Stream rather than loading a potentially very large supplier feed into memory.
    stream = SanitizedXML(source)
    context = ET.iterparse(stream, events=("start", "end"))
    _, root = next(context)
    for event, element in context:
        if event == "end" and element.tag == "product":
            record = parse_product(element)
            if record:
                products[record["external_id"]] = record
            root.clear()
    stream.close()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=destination.parent, prefix=".catalogue-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(list(products.values()), handle, ensure_ascii=False)
        os.replace(tmp, destination)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return len(products)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml", type=Path, help="Genuine Matterhorn productsAUD.xml file")
    args = parser.parse_args()
    if not args.xml.is_file():
        parser.error("XML file not found")
    print(f"Imported {import_xml(args.xml)} source-backed products into {OUTPUT}")
