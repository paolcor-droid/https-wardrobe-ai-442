import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_price_snapshots import compare


def test_price_drop_detected():
    old = [{"product_id": "a", "price_aud": 50}, {"product_id": "b", "price_aud": 20}]
    new = [{"product_id": "a", "price_aud": 40}, {"product_id": "b", "price_aud": 25}]
    assert compare(old, new) == [{
        "product_id": "a", "previous_price_aud": "50",
        "current_price_aud": "40", "drop_aud": "10",
    }]


def test_missing_and_invalid_prices_ignored():
    assert compare([{"product_id": "x", "price_aud": -1}], [{"product_id": "x", "price_aud": 2}]) == []
