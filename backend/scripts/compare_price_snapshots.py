"""Compare two independently sourced retailer price snapshots offline.

No invented prices or notifications. Feed must be licensed/authorised, contain
stable product IDs and AUD prices, and be refreshed by an external integration.
This tool does not connect to retailers, send alerts, or read customer records.

Usage: python scripts/compare_price_snapshots.py old.json new.json

Each JSON file: [{"product_id":"...", "price_aud":29.99}, ...]
"""
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


def parse_prices(records):
    result = {}
    for row in records:
        key = str(row.get("product_id", "")).strip()
        try:
            price = Decimal(str(row["price_aud"]))
        except (KeyError, InvalidOperation, TypeError):
            continue
        if key and price > 0 and price.is_finite():
            result[key] = price
    return result


def compare(old, new):
    before, after = parse_prices(old), parse_prices(new)
    changes = []
    for product_id in sorted(before.keys() & after.keys()):
        previous, current = before[product_id], after[product_id]
        if current < previous:
            changes.append({
                "product_id": product_id,
                "previous_price_aud": str(previous),
                "current_price_aud": str(current),
                "drop_aud": str(previous - current),
            })
    return changes


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: compare_price_snapshots.py OLD_JSON NEW_JSON")
    old = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    new = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    print(json.dumps({"price_drops": compare(old, new),
                      "notifications_sent": 0,
                      "note": "Offline comparison only; no live feed or alert delivery."}, indent=2))
