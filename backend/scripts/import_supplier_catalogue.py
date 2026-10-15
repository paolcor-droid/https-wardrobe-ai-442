"""Offline import of authorised supplier CSV or JSON into a private LUMIÈRE snapshot.

No network calls, databases, uploads, credentials or existing customer records.
Input column mapping is explicit: a supplier feed must not be assumed compatible.
Example:
 python scripts/import_supplier_catalogue.py --provider brandsdistribution --input sample.csv --mapping mapping.json --output /tmp/catalogue.json
Mapping JSON: {"external_id":"SKU","name":"Title","price":"Price","currency":"Currency","image_url":"ImageURL","category":"Category","department":"Department","colour_names":"Colour","sizes":"Sizes"}
List values may be delimited by |. Only approved wholesale provider IDs are supported.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path
from services.catalogue_providers import normalize_product, get_provider

ALLOWED = {"brandsdistribution", "romanelli-b2b", "matterhorn", "vaitto"}
MAX_BYTES = 100 * 1024 * 1024
LIST_FIELDS = {"colour_names", "sizes", "materials", "occasions", "palette_tags"}
FIELDS = {"external_id", "name", "brand", "category", "category_path",
          "description", "price", "currency", "image_url", "source_url",
          "colour_names", "sizes", "materials", "availability", "department",
          "occasions", "palette_tags"}


def records(path: Path):
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Supplier export exceeds 100 MB safety limit")
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            yield from csv.DictReader(stream)
    elif path.suffix.lower() == ".json":
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
        if not isinstance(data, list):
            raise ValueError("JSON supplier export must be an array of objects")
        yield from data
    else:
        raise ValueError("Only CSV and JSON supplier exports are supported")


def transform(row: dict, mapping: dict, provider: str):
    if not isinstance(row, dict):
        raise ValueError("Supplier record must be an object")
    raw = {}
    for field, column in mapping.items():
        if field not in FIELDS or not isinstance(column, str):
            raise ValueError("Invalid supplier field mapping")
        value = row.get(column)
        if value is None or value == "":
            continue
        if field in LIST_FIELDS:
            raw[field] = ([part.strip() for part in value.split("|") if part.strip()]
                          if isinstance(value, str) else value)
            if not isinstance(raw[field], list):
                raise ValueError("Expected list for " + field)
        else:
            raw[field] = value
    item = normalize_product(provider, raw)
    if item["provider_kind"] != "wholesale":
        raise ValueError("Retailer feed cannot be loaded as wholesale")
    return item


def import_feed(provider: str, source: Path, mapping: dict, destination: Path) -> dict:
    if provider not in ALLOWED or get_provider(provider).kind != "wholesale":
        raise ValueError("Provider not approved for offline wholesale import")
    if not {"external_id", "name"}.issubset(mapping):
        raise ValueError("Map the supplier ID and product name explicitly")
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output cannot be identical")
    # Avoid overwriting prior supplier snapshots; stage under a new destination.
    if destination.exists():
        raise FileExistsError("Destination already exists; refusing overwrite")
    seen = set()
    imported = []
    invalid = 0
    for index, row in enumerate(records(source)):
        if index >= 100_000:
            raise ValueError("More than 100,000 rows; split the feed")
        try:
            product = transform(row, mapping, provider)
            key = (provider, product["external_id"])
            if key in seen:
                invalid += 1
                continue
            seen.add(key)
            imported.append(product)
        except (ValueError, TypeError):
            invalid += 1
    if not imported:
        raise ValueError("No valid supplier records; output not written")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(dir=destination.parent, prefix=".import-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(imported, stream, ensure_ascii=False)
        # Exclusive destination creation: no replacement of an existing snapshot.
        os.link(temp, destination)
    finally:
        Path(temp).unlink(missing_ok=True)
    return {"provider": provider, "imported": len(imported), "skipped": invalid,
            "output": str(destination)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", required=True, choices=sorted(ALLOWED))
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    print(json.dumps(import_feed(args.provider, args.input, mapping, args.output)))


if __name__ == "__main__":
    main()
