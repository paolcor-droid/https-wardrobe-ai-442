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


def test_confirmed_season_and_occasion_labels_affect_ranking():
    from services.wardrobe_compatibility import score_owned_outfit
    business = [own("shirt", "top", "cream", "business"),
                {**own("trousers", "bottom", "navy", "classic"), "season": "cool weather"}]
    formal_cold = score_owned_outfit(business, occasion="business", climate="cold")
    casual_hot = score_owned_outfit(business, occasion="casual", climate="hot")
    assert formal_cold["compatibility_score"] >= casual_hot["compatibility_score"]
    assert formal_cold["image_colour_verified"] is False


def test_missing_shoes_are_matched_to_top_and_bottom_not_two_tops():
    wardrobe = [
        own("shirt-a", "top", "navy"), own("shirt-b", "top", "cream"),
        own("trousers", "bottom", "grey"),
    ]
    result = mixed_outfits(wardrobe, [supplier("loafers", "shoes")])
    shoe_looks = [row for row in result["outfits"] if row["purchase_required"]]
    assert shoe_looks
    anchors = shoe_looks[0]["owned_ids"]
    assert "trousers" in anchors
    assert sum(item in anchors for item in ("shirt-a", "shirt-b")) == 1
    assert shoe_looks[0]["suggested_products"][0]["category"] == "shoes"


def test_missing_shoes_rankings_consider_selected_weather():
    wardrobe = [
        own("shirt", "top", "navy"), own("trousers", "bottom", "cream")
    ]
    products = [supplier("sandals", "shoes", "tan")]
    hot = mixed_outfits(wardrobe, products, preferences={"climate": "hot"})
    cold = mixed_outfits(wardrobe, products, preferences={"climate": "cold"})
    assert any(r["purchase_required"] for r in hot["outfits"])
    assert any(r["purchase_required"] for r in cold["outfits"])


def test_optional_missing_shoes_remain_visible_with_many_owned_base_looks():
    wardrobe = [own("shirt-" + str(i), "top") for i in range(5)]
    wardrobe += [own("pants-" + str(i), "bottom") for i in range(3)]
    result = mixed_outfits(wardrobe, [supplier("shoes", "shoes")], limit=8)
    assert len(result["outfits"]) <= 8
    assert result["outfits"][0]["purchase_required"] is False
    assert any(row["purchase_required"] for row in result["outfits"])


def test_legacy_digest_feedback_does_not_generalise_without_garment_ids():
    from hashlib import sha256
    import json
    wardrobe = [own("navy", "top", "navy"), own("red", "top", "red"),
                own("bottom", "bottom", "cream")]
    before = mixed_outfits(wardrobe, [])["outfits"]
    target = before[0]["owned_ids"]
    digest = sha256(json.dumps(sorted(target)).encode()).hexdigest()
    after = mixed_outfits(wardrobe, [], feedback=[
        {"product_id": "owned-outfit:" + digest, "sentiment": "disliked"},
    ])["outfits"]
    scores_before = {tuple(row["owned_ids"]): row["score"] for row in before}
    scores_after = {tuple(row["owned_ids"]): row["score"] for row in after}
    assert scores_after[tuple(target)] < scores_before[tuple(target)]
    other = next(row["owned_ids"] for row in before if row["owned_ids"] != target)
    assert scores_after[tuple(other)] == scores_before[tuple(other)]


def test_malformed_legacy_feedback_does_not_affect_rankings():
    wardrobe = [own("shirt", "top"), own("trousers", "bottom")]
    original = mixed_outfits(wardrobe, [])["outfits"]
    after = mixed_outfits(wardrobe, [], feedback=[
        {"product_id": "owned-outfit:invalid", "sentiment": "disliked"},
    ])["outfits"]
    assert after == original
