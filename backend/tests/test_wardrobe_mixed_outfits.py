"""Synthetic wardrobe-first recommendation tests; no live supplier access or AI calls."""
from services.wardrobe_mixed_outfits import mixed_outfits


def own(identifier, category, colour="navy", style="classic"):
    return {"id": identifier, "name": identifier, "category": category,
            "colour": colour, "style": style}


def supplier(identifier, category, colour="cream"):
    return {"product_id": identifier, "name": "Sample " + identifier,
            "category": category, "colour_names": [colour],
            "price": 30, "currency": "AUD", "image_url": None}


def test_complete_owned_outfits_never_push_unneeded_purchases():
    result = mixed_outfits(
        [own("shirt", "top"), own("trousers", "bottom"), own("shoes", "shoes")],
        [supplier("buy-shoes", "shoes"), supplier("buy-top", "top")])
    assert result["outfits"]
    assert all(not outfit["purchase_required"] for outfit in result["outfits"])
    assert all(outfit["suggested_products"] == [] for outfit in result["outfits"])


def test_only_missing_role_is_suggested_and_price_stock_never_verified():
    result = mixed_outfits(
        [own("shirt", "top")],
        [supplier("missing-bottom", "bottom"), supplier("unneeded-top", "top")])
    assert result["outfits"]
    look = result["outfits"][0]
    assert look["owned_ids"] == ["shirt"]
    assert look["purchase_required"]
    assert len(look["suggested_products"]) == 1
    product = look["suggested_products"][0]
    assert product["product_id"] == "missing-bottom"
    assert product["price_verified"] is False
    assert product["stock_verified"] is False


def test_empty_wardrobe_does_not_create_catalogue_only_purchases():
    result = mixed_outfits([], [supplier("top", "top")])
    assert result["outfits"] == []


def test_feedback_reorders_owned_looks_without_cross_account_inputs():
    from hashlib import sha256
    import json
    wardrobe = [own("navy", "top", "navy"), own("red", "top", "red"),
                own("bottom", "bottom", "cream")]
    before = mixed_outfits(wardrobe, [])["outfits"]
    assert len(before) == 2
    disfavoured = before[0]
    digest = sha256(json.dumps(sorted(disfavoured["owned_ids"])).encode()).hexdigest()
    after = mixed_outfits(wardrobe, [], feedback=[{
        "product_id": "owned-outfit:" + digest, "sentiment": "disliked",
    }])["outfits"]
    assert after[0]["owned_ids"] != disfavoured["owned_ids"]


def test_confirmed_colour_and_style_changes_adjust_ranking():
    wardrobe = [own("blue", "top", "navy", "classic"),
                own("orange", "top", "orange", "casual"),
                own("trousers", "bottom", "cream", "classic")]
    profile = {"style": "classic", "avoided_colours": ["orange"]}
    first = mixed_outfits(wardrobe, [], preferences=profile)["outfits"][0]
    assert first["owned_ids"][0] == "blue"
    wardrobe[0]["colour"] = "orange"
    wardrobe[0]["style"] = "casual"
    wardrobe[1]["colour"] = "navy"
    wardrobe[1]["style"] = "classic"
    second = mixed_outfits(wardrobe, [], preferences=profile)["outfits"][0]
    assert second["owned_ids"][0] == "orange"


def test_scan_named_colours_affect_complete_outfit_score():
    wardrobe = [own("shirt", "top", "soft navy"), own("pants", "bottom", "cream")]
    scan = {"best_neutrals": [{"name": "navy"}, {"name": "cream"}]}
    with_scan = mixed_outfits(wardrobe, [], scan=scan)["outfits"][0]["score"]
    without_scan = mixed_outfits(wardrobe, [])["outfits"][0]["score"]
    assert with_scan >= without_scan
