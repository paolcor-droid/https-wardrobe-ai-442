from services.catalogue_providers import normalize_product
from services.product_recommendations import rank_verified_products, customer_product_view


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


def test_wholesale_product_can_be_verified_without_public_supplier_url():
    product = _product(
        provider_id="matterhorn",
        external_id="mh-1",
        source_url=None,
        colour_names=["olive"],
    )
    assert product["source_verified"] is True
    assert product["source_url"] is None
    ranked = rank_verified_products([product], _profile())
    assert ranked and ranked[0]["external_id"] == "mh-1"


def test_customer_storefront_strips_supplier_identity_and_source_metadata():
    product = _product(
        provider_id="matterhorn",
        external_id="mh-private",
        source_url=None,
        colour_names=["olive"],
    )
    product["_matterhorn"] = {"ean": "private", "stock": 4}
    product["recommendation_score"] = 80
    product["recommendation_reasons"] = ["Olive suits your skin analysis."]
    public = customer_product_view(product)
    assert public["product_id"] == "mh-private"
    assert "provider_id" not in public
    assert "source_url" not in public
    assert "availability" not in public
    assert "_matterhorn" not in public


def test_rank_excludes_out_of_stock_verified_product():
    product = _product(
        provider_id="matterhorn",
        external_id="mh-oos",
        source_url=None,
        colour_names=["olive"],
        availability="0",
    )
    assert rank_verified_products([product], _profile()) == []


def test_rank_accepts_in_stock_verified_wholesale_product():
    product = _product(
        provider_id="matterhorn",
        external_id="mh-stock",
        source_url=None,
        colour_names=["olive"],
        availability="4",
    )
    ranked = rank_verified_products([product], _profile())
    assert ranked and ranked[0]["external_id"] == "mh-stock"
