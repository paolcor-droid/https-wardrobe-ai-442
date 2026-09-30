from services.catalogue_providers import normalize_product
from services.matterhorn_trial_snapshot import MATTERHORN_TRIAL_SNAPSHOT
from services.product_recommendations import customer_recommendations, rank_verified_products


def _profile():
    return {
        "skin": {
            "undertone": "neutral_warm",
            "best_neutrals": [{"name": "Soft Navy", "hex": "#35445A"}],
            "best_accents": [{"name": "Olive", "hex": "#727442"}],
            "statement_colours": [],
            "caution_colours": [{"name": "Charcoal", "hex": "#414247"}],
        },
        "preferences": {
            "budget_min": 0,
            "budget_max": 100,
            "occasion": "casual",
            "categories": [],
            "climate": "hot",
            "style": "relaxed",
            "preferred_colours": [],
            "avoided_colours": [],
            "preferred_retailers": [],
        },
    }


def test_real_snapshot_produces_customer_safe_personalised_cards():
    products = [normalize_product("matterhorn", raw) for raw in MATTERHORN_TRIAL_SNAPSHOT]
    ranked = rank_verified_products(products, _profile(), limit=12)
    public = customer_recommendations(ranked)
    assert public
    assert any(item["product_id"] == "111506" for item in public)
    assert all(item["price"] is None for item in public)
    for item in public:
        assert "provider_id" not in item
        assert "provider_kind" not in item
        assert "source_url" not in item
        assert "availability" not in item
        assert item["recommendation_reasons"]
