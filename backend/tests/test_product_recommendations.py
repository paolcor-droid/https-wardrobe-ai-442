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
        "skin": {
            "undertone": "neutral_warm",
            "depth": "light",
            "chroma": "muted",
            "contrast": "medium",
            "season": "spring",
            "best_neutrals": [{"name": "Soft Navy", "hex": "#35445A"}],
            "best_accents": [{"name": "Olive", "hex": "#727442"}, {"name": "Deep Teal", "hex": "#1F6262"}],
            "statement_colours": [{"name": "Deep Teal", "hex": "#1F6262"}],
            "caution_colours": [{"name": "Charcoal", "hex": "#414247"}],
        },
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


def test_scan_named_palette_outranks_generic_undertone_match():
    scan_match = _product(
        provider_id="zara",
        external_id="scan-match",
        name="Olive Linen Shirt",
        colour_names=["olive"],
        palette_tags=[],
        price=100,
    )
    generic = _product(
        provider_id="zara",
        external_id="generic",
        name="Tan Linen Shirt",
        colour_names=["tan"],
        palette_tags=["warm"],
        price=100,
    )
    ranked = rank_verified_products([generic, scan_match], _profile(preferred_colours=[]))
    assert [item["external_id"] for item in ranked][:2] == ["scan-match", "generic"]
    assert "skin analysis" in ranked[0]["recommendation_reasons"][0].lower()


def test_scan_caution_colour_is_penalised():
    caution = _product(
        provider_id="zara",
        external_id="caution",
        name="Charcoal Linen Shirt",
        colour_names=["charcoal"],
        palette_tags=["neutral"],
        price=100,
    )
    recommended = _product(
        provider_id="zara",
        external_id="recommended",
        name="Olive Linen Shirt",
        colour_names=["olive"],
        palette_tags=[],
        price=100,
    )
    ranked = rank_verified_products([caution, recommended], _profile(preferred_colours=[]))
    assert ranked[0]["external_id"] == "recommended"
    caution_result = next(item for item in ranked if item["external_id"] == "caution")
    assert any("caution" in reason.lower() for reason in caution_result["recommendation_reasons"])
