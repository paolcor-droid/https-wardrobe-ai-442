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
    assert [item["external_id"] for item in ranked] == ["match"]
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
    assert [item["external_id"] for item in ranked] == ["scan-match"]
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
    assert all(item["external_id"] != "caution" for item in ranked)


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


def test_customer_storefront_never_falls_back_to_wholesale_cost():
    product = _product(
        provider_id="matterhorn",
        external_id="mh-cost-private",
        source_url=None,
        price=20.90,
        colour_names=["olive"],
    )
    public = customer_product_view(product)
    assert public["price"] is None


def test_missing_supplier_occasion_metadata_is_not_false_mismatch():
    product = _product(
        provider_id="matterhorn",
        external_id="mh-unknown-occasion",
        source_url=None,
        occasions=[],
        availability="2",
        colour_names=["olive"],
    )
    ranked = rank_verified_products([product], _profile(occasion="casual"))
    assert ranked and ranked[0]["external_id"] == "mh-unknown-occasion"


def test_supplier_navy_blue_matches_soft_navy_scan_colour():
    product = _product(
        provider_id="matterhorn",
        external_id="mh-navy",
        source_url=None,
        occasions=[],
        availability="2",
        colour_names=["navy blue"],
        palette_tags=[],
    )
    ranked = rank_verified_products([product], _profile(preferred_colours=[]))
    assert ranked
    assert any("neutral" in reason.lower() for reason in ranked[0]["recommendation_reasons"])


def test_customer_storefront_strips_provider_kind_too():
    product = _product(provider_id="matterhorn", source_url=None, availability="2")
    public = customer_product_view(product)
    assert "provider_kind" not in public


def test_v2_excludes_explicitly_avoided_palette_colour():
    product = _product(
        external_id="avoid-navy",
        colour_names=["navy"],
    )
    profile = _profile(avoided_colours=["navy"])
    assert rank_verified_products([product], profile) == []


def test_v2_accepts_preferred_colour_outside_scan_palette():
    product = _product(
        external_id="preferred-coral",
        name="Coral Linen Shirt",
        colour_names=["coral"],
    )
    profile = _profile(preferred_colours=["coral"], avoided_colours=[])
    ranked = rank_verified_products([product], profile)
    assert len(ranked) == 1
    assert ranked[0]["external_id"] == "preferred-coral"


def test_v2_excludes_product_without_verified_colour_names():
    product = _product(
        external_id="unknown-colour",
        colour_names=[],
    )
    assert rank_verified_products([product], _profile()) == []


def test_v2_without_scan_requires_preferred_colour():
    product = _product(
        external_id="no-scan",
        colour_names=["navy"],
    )
    profile = _profile(preferred_colours=[], avoided_colours=[])
    profile["skin"] = None
    assert rank_verified_products([product], profile) == []

    profile["preferences"]["preferred_colours"] = ["navy"]
    assert len(rank_verified_products([product], profile)) == 1


def test_v2_generic_blue_does_not_claim_soft_navy_match():
    product = _product(
        external_id="generic-blue",
        colour_names=["blue"],
        palette_tags=[],
    )
    profile = _profile(preferred_colours=[], avoided_colours=[])
    assert rank_verified_products([product], profile) == []


def test_v2_navy_blue_remains_compatible_with_soft_navy():
    product = _product(
        external_id="navy-blue",
        colour_names=["navy blue"],
        palette_tags=[],
    )
    profile = _profile(preferred_colours=[], avoided_colours=[])
    assert len(rank_verified_products([product], profile)) == 1


def test_v2_multicolor_without_component_colours_is_not_verified():
    product = _product(
        external_id="unknown-multicolor",
        colour_names=["multicolor"],
        palette_tags=[],
    )
    profile = _profile(preferred_colours=[], avoided_colours=[])
    assert rank_verified_products([product], profile) == []


def test_colour_reason_does_not_use_description_only():
    from services.recommendation_engine import recommendation_reasons

    product = {
        "name": "Navy shirt",
        "description": "Features black buttons",
        "colour_names": ["navy blue"],
        "palette_tags": [],
    }

    reasons = recommendation_reasons(
        product,
        colour_profile=None,
        occasion=None,
        climate=None,
        preferred_colours=["black"],
    )

    assert not any("preferred clothing colours" in reason for reason in reasons)


def test_preferred_colour_reason_uses_verified_colour():
    from services.recommendation_engine import recommendation_reasons

    product = {
        "name": "Olive blouse",
        "description": "",
        "colour_names": ["olive"],
        "palette_tags": [],
    }

    reasons = recommendation_reasons(
        product,
        colour_profile=None,
        occasion=None,
        climate=None,
        preferred_colours=["olive"],
    )

    assert any(
        "Olive" in reason and "preferred clothing colours" in reason
        for reason in reasons
    )


def test_two_distinct_profiles_get_distinct_verified_outfits():
    """Synthetic customer profiles must never share an assumed default palette."""
    navy = _product(external_id="navy-profile", name="Navy Linen Shirt", colour_names=["navy"], palette_tags=[])
    olive = _product(provider_id="zara", external_id="olive-profile", name="Olive Linen Shirt",
                     colour_names=["olive"], palette_tags=[])
    one = _profile(preferred_colours=["navy"], avoided_colours=["olive"])
    two = _profile(preferred_colours=["olive"], avoided_colours=["navy"])
    ranked_one = rank_verified_products([navy, olive], one)
    ranked_two = rank_verified_products([navy, olive], two)
    assert [p["external_id"] for p in ranked_one] == ["navy-profile"]
    assert [p["external_id"] for p in ranked_two] == ["olive-profile"]
    assert ranked_one[0]["recommendation_reasons"]
    assert ranked_two[0]["recommendation_reasons"]
