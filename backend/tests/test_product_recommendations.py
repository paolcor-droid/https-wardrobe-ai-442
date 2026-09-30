from services.catalogue_providers import normalize_product
from services.product_recommendations import rank_verified_products


def _profile(**overrides):
    preferences = {
        "budget_min": 50,
        "budget_max": 250,
        "occasion": "casual",
        "categories": [],
        "climate": "hot",
        "style": "relaxed",
        "preferred_colours": ["navy"],
        "avoided_colours": ["black"],
        "preferred_retailers": ["uniqlo"],
    }
    preferences.update(overrides)
    return {
        "skin": {"undertone": "neutral_warm"},
        "preferences": preferences,
    }


def _product(provider_id="uniqlo", **overrides):
    raw = {
        "external_id": "verified-1",
        "name": "Navy Linen Shirt",
        "source_url": "https://example.com/product/verified-1",
        "price": 99,
        "category": "shirt",
        "description": "Lightweight linen shirt",
        "colour_names": ["navy"],
        "occasions": ["casual"],
        "palette_tags": ["warm", "neutral"],
    }
    raw.update(overrides)
    return normalize_product(provider_id, raw)


def test_normalize_rejects_unknown_provider():
    try:
        _product("invented-store")
        assert False, "Expected unknown provider to be rejected"
    except ValueError as exc:
        assert "Unknown catalogue provider" in str(exc)


def test_normalize_rejects_missing_source_url():
    try:
        _product(source_url="")
        assert False, "Expected missing source URL to be rejected"
    except ValueError as exc:
        assert "source_url" in str(exc)


def test_normalize_rejects_non_http_source_url():
    try:
        _product(source_url="not-a-real-url")
        assert False, "Expected invalid source URL to be rejected"
    except ValueError as exc:
        assert "absolute http" in str(exc)


def test_rank_excludes_over_budget_product():
    product = _product(price=300)
    assert rank_verified_products([product], _profile()) == []


def test_rank_excludes_hot_weather_heavy_product():
    product = _product(name="Heavy Wool Blazer", description="heavy wool blazer")
    assert rank_verified_products([product], _profile()) == []


def test_rank_prefers_matching_verified_product():
    matching = _product(external_id="match", name="Navy Linen Shirt", price=100)
    less_matching = _product(
        provider_id="zara",
        external_id="other",
        name="Beige Shirt",
        description="lightweight shirt",
        colour_names=["beige"],
        price=100,
    )
    ranked = rank_verified_products([less_matching, matching], _profile())
    assert [item["external_id"] for item in ranked] == ["match", "other"]
    assert ranked[0]["recommendation_reasons"]
