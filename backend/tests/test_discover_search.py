"""Regression coverage for Discover identity, filters and strict pagination."""
from services.discover_search import product_key, matches, paginate, catalogue_view


def item(provider, id, *, colour="Navy", size="M", price=100):
    return {"provider_id": provider, "external_id": id, "name": "Linen shirt",
            "brand": "Demo Brand", "category": "Shirts", "colour_names": [colour],
            "sizes": [size], "customer_price": price, "recommendation_score": 50}


def test_provider_identity_prevents_collision():
    first = item("matterhorn", "123")
    second = item("vaitto", "123")
    assert product_key(first) != product_key(second)
    assert product_key(first) == product_key(dict(first))


def test_multiple_filters_and_price_boundaries():
    product = item("vaitto", "1")
    assert matches(product, {"q": "linen", "brand": "demo", "category": "shirt",
                             "colour": "navy", "size": "m", "min_price": 100,
                             "max_price": 100})
    assert not matches(product, {"colour": "red"})
    assert not matches(product, {"size": "L"})
    assert not matches(product, {"max_price": 99})


def test_page_has_no_duplicate_products():
    values = [item("vaitto", str(i)) for i in range(50)]
    first, total = paginate(values, {}, page=1, per_page=20)
    second, _ = paginate(values, {}, page=2, per_page=20)
    assert total == 50
    assert len(first) == len(second) == 20
    assert {product_key(x) for x in first}.isdisjoint(product_key(x) for x in second)


def test_customer_projection_does_not_claim_live_stock():
    product = item("vaitto", "123")
    result = catalogue_view(product, lambda p: {"name": p["name"]})
    assert result["tryon_supported"] is False
    assert result["tryon_product_id"] is None
    assert result["price_status"] == "supplier_snapshot"
    assert result["stock_status"] == "unverified_snapshot"
