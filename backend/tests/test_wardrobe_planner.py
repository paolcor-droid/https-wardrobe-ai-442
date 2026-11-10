from services.wardrobe_planner import capsule_plan, plan_outfits


def test_two_piece_outfit():
    items = [
        {"id": "shirt", "name": "Linen shirt", "category": "top"},
        {"id": "trousers", "name": "Cotton trousers", "category": "bottom"},
    ]
    outfits = plan_outfits(items)
    assert len(outfits) == 1
    assert outfits[0]["item_ids"] == ["shirt", "trousers"]
    assert outfits[0]["image_colour_verified"] is False


def test_hot_weather_does_not_add_coat():
    items = [
        {"id": "top", "name": "Top", "category": "top"},
        {"id": "bottom", "name": "Bottom", "category": "bottom"},
        {"id": "coat", "name": "Coat", "category": "outerwear"},
    ]
    assert "coat" not in plan_outfits(items, climate="hot")[0]["item_ids"]
    assert "coat" in plan_outfits(items, climate="cold")[0]["item_ids"]


def test_capsule_identifies_missing_bottom():
    result = capsule_plan([{"id": "top", "name": "Top", "category": "top"}])
    assert "a versatile bottom" in result["missing_categories"]


def test_rotates_shoes_instead_of_always_first():
    items = [
        {"id": "top", "name": "Top", "category": "top"},
        {"id": "bottom1", "name": "Bottom one", "category": "bottom"},
        {"id": "bottom2", "name": "Bottom two", "category": "bottom"},
        {"id": "shoes1", "name": "Shoes one", "category": "shoes"},
        {"id": "shoes2", "name": "Shoes two", "category": "shoes"},
    ]
    outfits = plan_outfits(items)
    assert len(outfits) == 4
    assert {o["item_ids"][-1] for o in outfits} == {"shoes1", "shoes2"}
    assert {o["item_ids"][1] for o in outfits} == {"bottom1", "bottom2"}


def test_dresses_work_without_tops_and_bottoms():
    items = [{"id": "dress", "name": "Summer dress", "category": "dress"}]
    assert plan_outfits(items, climate="hot")[0]["item_ids"] == ["dress"]


def test_soft_deleted_wardrobe_items_are_excluded():
    items = [
        {"id": "top", "name": "Top", "category": "top"},
        {"id": "bottom", "name": "Bottom", "category": "bottom", "deleted_at": "2026-01-01"},
    ]
    assert plan_outfits(items) == []


def test_invalid_limit_rejected():
    import pytest
    with pytest.raises(ValueError):
        plan_outfits([], limit=0)


def test_capsule_balances_categories_before_extra_tops():
    items = [{"id": f"top{i}", "name": f"A top {i}", "category": "top"} for i in range(8)]
    items += [
        {"id": "bottom", "name": "Z trousers", "category": "bottom"},
        {"id": "shoes", "name": "Z shoes", "category": "shoes"},
    ]
    result = capsule_plan(items, max_items=4)
    selected = {item["id"] for item in result["items"]}
    assert {"bottom", "shoes"}.issubset(selected)
    assert result["possible_outfits"]


def test_wardrobe_duplicates_only_from_matching_labels():
    from services.wardrobe_planner import wardrobe_insights
    items = [
        {"id": "one", "name": " Blue Shirt ", "category": "top", "colour": "Blue"},
        {"id": "two", "name": "blue  shirt", "category": "top", "colour": "blue"},
        {"id": "three", "name": "Different shirt", "category": "top", "colour": "blue"},
    ]
    insights = wardrobe_insights(items)
    assert len(insights["possible_duplicates"]) == 1
    assert insights["possible_duplicates"][0]["item_ids"] == ["one", "two"]


def test_capsule_rejects_zero_capacity():
    import pytest
    with pytest.raises(ValueError):
        capsule_plan([], max_items=0)


def test_single_base_outfit_offers_alternative_owned_shoes():
    items = [
        {"id": "top", "name": "Linen top", "category": "top"},
        {"id": "bottom", "name": "Trousers", "category": "bottom"},
        {"id": "trainers", "name": "Trainers", "category": "shoes"},
        {"id": "sandals", "name": "Sandals", "category": "shoes"},
    ]
    outfits = plan_outfits(items, climate="hot")
    assert [outfit["item_ids"][-1] for outfit in outfits] == ["trainers", "sandals"]
    assert len(plan_outfits(items, climate="hot", limit=1)) == 1


def test_named_scan_and_confirmed_garment_styles_change_order():
    items = [
        {"id": "blue", "name": "Blue shirt", "category": "top", "colour": "navy", "style": "classic"},
        {"id": "orange", "name": "Orange shirt", "category": "top", "colour": "orange", "style": "streetwear"},
        {"id": "trousers", "name": "Trousers", "category": "bottom", "colour": "cream", "style": "classic"},
    ]
    scan = {"best_neutrals": [{"name": "Soft Navy"}, {"name": "Cream"}],
            "caution_colours": [{"name": "Orange"}]}
    ranked = plan_outfits(items, scan=scan, preferred_style="classic")
    assert ranked[0]["item_ids"][0] == "blue"
    assert ranked[0]["compatibility_score"] > ranked[1]["compatibility_score"]
    assert ranked[0]["ranking_basis"] == "calibrated_confirmed_wardrobe_labels_and_named_scan_swatches"
    assert not ranked[0]["image_colour_verified"]


def test_user_avoidance_can_change_outfit_ranking():
    items = [
        {"id": "red", "name": "Red top", "category": "top", "colour": "red"},
        {"id": "green", "name": "Green top", "category": "top", "colour": "green"},
        {"id": "bottom", "name": "Bottom", "category": "bottom"},
    ]
    assert plan_outfits(items, avoided_colours=["red"])[0]["item_ids"][0] == "green"
    assert plan_outfits(items, avoided_colours=["green"])[0]["item_ids"][0] == "red"


def test_unlabelled_garments_are_not_claimed_colour_verified():
    outfits = plan_outfits([
        {"id": "a", "name": "Top", "category": "top"},
        {"id": "b", "name": "Bottom", "category": "bottom"},
    ], scan={"best_accents": [{"name": "Rose"}]})
    assert outfits[0]["image_colour_verified"] is False
    assert "Add confirmed garment colours" in outfits[0]["reason"]


def test_capsule_passes_skin_scan_and_style_to_outfit_ranking():
    items = [
        {"id": "a", "name": "Warm top", "category": "top", "colour": "rose", "style": "romantic"},
        {"id": "b", "name": "Bottom", "category": "bottom", "colour": "cream"},
    ]
    capsule = capsule_plan(items, scan={"best_accents": [{"name": "Soft Rose"}]},
                           preferred_style="romantic")
    assert capsule["possible_outfits"][0]["compatibility_score"] > 50
    assert "saved scan" in capsule["possible_outfits"][0]["reason"]


def test_capsule_prefers_colour_compatible_top_over_alphabetical_first():
    items = [
        {"id": "orange", "name": "A orange shirt", "category": "top",
         "colour": "orange", "style": "streetwear"},
        {"id": "blue", "name": "Z navy shirt", "category": "top",
         "colour": "navy", "style": "classic"},
        {"id": "bottom", "name": "Cream trousers", "category": "bottom",
         "colour": "cream", "style": "classic"},
    ]
    capsule = capsule_plan(
        items, max_items=2,
        scan={"best_neutrals": [{"name": "Navy"}, {"name": "Cream"}],
              "caution_colours": [{"name": "Orange"}]},
        preferred_style="classic",
    )
    assert {item["id"] for item in capsule["items"]} == {"blue", "bottom"}
    assert capsule["possible_outfits"]
    assert capsule["possible_outfits"][0]["item_ids"] == ["blue", "bottom"]


def test_capsule_explains_missing_shoes_and_weather_layer():
    items = [{"id": "top", "name": "Sweater", "category": "top", "season": "cool weather"},
             {"id": "bottom", "name": "Trousers", "category": "bottom"}]
    capsule = capsule_plan(items, climate="cold")
    assert "shoes suited to your occasion" in capsule["missing_categories"]
    assert "a layer for colder weather" in capsule["missing_categories"]
    assert capsule["possible_outfits"]


def test_owned_accessory_is_included_in_recommended_outfit():
    items = [
        {"id": "shirt", "name": "Shirt", "category": "top"},
        {"id": "trousers", "name": "Trousers", "category": "bottom"},
        {"id": "shoes", "name": "Shoes", "category": "shoes"},
        {"id": "belt", "name": "Belt", "category": "accessory"},
    ]
    outfits = plan_outfits(items, climate="mild")
    assert len(outfits) == 1
    assert outfits[0]["item_ids"] == ["shirt", "trousers", "shoes", "belt"]


def test_cold_weather_outfit_includes_owned_layer_and_accessory():
    items = [
        {"id": "shirt", "name": "Shirt", "category": "top"},
        {"id": "trousers", "name": "Trousers", "category": "bottom"},
        {"id": "coat", "name": "Coat", "category": "outerwear"},
        {"id": "scarf", "name": "Scarf", "category": "accessory"},
    ]
    outfits = plan_outfits(items, climate="cold")
    assert {"shirt", "trousers", "coat", "scarf"} == set(outfits[0]["item_ids"])
    hot_outfits = plan_outfits(items, climate="hot")
    assert "coat" not in hot_outfits[0]["item_ids"]


def test_visually_duplicate_uploads_do_not_repeat_identical_looks():
    items = [
        {"id": "shirt1", "name": "Button-up shirt", "category": "top", "colour": "navy", "style": "classic"},
        {"id": "shirt2", "name": " Button-up  shirt ", "category": "top", "colour": "Navy", "style": "classic"},
        {"id": "shirt3", "name": "Button-up shirt", "category": "top", "colour": "light blue", "style": "classic"},
        {"id": "pants", "name": "Trousers", "category": "bottom", "colour": "grey"},
    ]
    outfits = plan_outfits(items)
    assert len(outfits) == 2
    assert {row["item_ids"][0] for row in outfits} <= {"shirt1", "shirt2", "shirt3"}
    assert any(row["item_ids"][0] == "shirt3" for row in outfits)


def test_outfit_completion_requires_shoes_but_not_optional_accessories():
    base = [
        {"id": "shirt", "name": "Navy shirt", "category": "top"},
        {"id": "trousers", "name": "Grey trousers", "category": "bottom"},
    ]
    without_shoes = plan_outfits(base, climate="mild")[0]
    assert without_shoes["is_complete"] is False
    assert without_shoes["missing_categories"] == ["shoes"]
    with_shoes = plan_outfits(base + [
        {"id": "shoes", "name": "Black shoes", "category": "shoes"},
    ], climate="mild")[0]
    assert with_shoes["is_complete"] is True
    assert with_shoes["missing_categories"] == []


def test_cold_weather_look_explains_missing_layer_without_hiding_shoes():
    base = [
        {"id": "shirt", "name": "Shirt", "category": "top"},
        {"id": "pants", "name": "Pants", "category": "bottom"},
        {"id": "shoes", "name": "Shoes", "category": "shoes"},
    ]
    cold = plan_outfits(base, climate="cold")[0]
    assert cold["is_complete"] is False
    assert cold["missing_categories"] == ["outerwear"]
    with_layer = plan_outfits(base + [
        {"id": "jacket", "name": "Jacket", "category": "outerwear"},
    ], climate="cold")[0]
    assert with_layer["is_complete"] is True
    assert with_layer["missing_categories"] == []
    hot = plan_outfits(base, climate="hot")[0]
    assert hot["is_complete"] is True


def test_outfit_scores_are_calibrated_not_perfect_even_with_many_matches():
    from services.wardrobe_compatibility import score_owned_outfit
    pieces = [
        {"id": "shirt", "name": "Shirt", "category": "top",
         "colour": "navy", "style": "classic"},
        {"id": "trousers", "name": "Trousers", "category": "bottom",
         "colour": "cream", "style": "classic"},
        {"id": "shoes", "name": "Shoes", "category": "shoes",
         "colour": "black", "style": "classic"},
    ]
    scan = {"best_neutrals": [{"name": "navy"}, {"name": "cream"}, {"name": "black"}]}
    strongest = score_owned_outfit(
        pieces, scan=scan, preferred_colours=["navy", "cream", "black"],
        preferred_style="classic", occasion="business")
    baseline = score_owned_outfit(pieces)
    assert 0 <= strongest["compatibility_score"] <= 95
    assert strongest["compatibility_score"] > baseline["compatibility_score"]
    assert strongest["image_colour_verified"] is False


def test_avoid_colours_and_weather_remain_effective_after_calibration():
    from services.wardrobe_compatibility import score_owned_outfit
    shirt = {"id": "shirt", "name": "Shirt", "category": "top",
             "colour": "navy", "style": "classic", "season": "cool weather"}
    trousers = {"id": "trousers", "name": "Trousers", "category": "bottom",
                "colour": "cream", "style": "classic"}
    good = score_owned_outfit([shirt, trousers], climate="cold")
    discouraged = score_owned_outfit(
        [shirt, trousers], avoided_colours=["navy"], climate="hot")
    assert good["compatibility_score"] > discouraged["compatibility_score"]
    assert discouraged["compatibility_score"] < 95


def test_saved_likes_and_dislikes_learn_from_similar_wardrobe_looks():
    wardrobe = [
        {"id": "navy", "name": "Navy shirt", "category": "top", "colour": "navy", "style": "classic"},
        {"id": "blue", "name": "Blue shirt", "category": "top", "colour": "navy", "style": "classic"},
        {"id": "orange", "name": "Orange shirt", "category": "top", "colour": "orange", "style": "streetwear"},
        {"id": "pants", "name": "Trousers", "category": "bottom", "colour": "cream", "style": "classic"},
    ]
    signal = [{
        "product_id": "owned-outfit:test", "wardrobe_item_ids": ["navy", "pants"],
        "sentiment": "liked",
    }]
    initial = {tuple(o["item_ids"]): o for o in plan_outfits(wardrobe)}
    learned = {tuple(o["item_ids"]): o for o in plan_outfits(wardrobe, feedback=signal)}
    assert learned[("navy", "pants")]["compatibility_score"] > initial[("navy", "pants")]["compatibility_score"]
    # A different saved shirt with the same confirmed colour and style also benefits.
    assert learned[("blue", "pants")]["compatibility_score"] > initial[("blue", "pants")]["compatibility_score"]
    assert learned[("orange", "pants")]["compatibility_score"] >= 0


def test_dislike_reduces_direct_look_score_without_disabling_other_outfits():
    wardrobe = [
        {"id": "shirt", "name": "Navy shirt", "category": "top", "colour": "navy"},
        {"id": "red", "name": "Red shirt", "category": "top", "colour": "red"},
        {"id": "pants", "name": "Cream pants", "category": "bottom", "colour": "cream"},
    ]
    before = {tuple(o["item_ids"]): o for o in plan_outfits(wardrobe)}
    after = {tuple(o["item_ids"]): o for o in plan_outfits(wardrobe, feedback=[{
        "product_id": "owned-outfit:test", "wardrobe_item_ids": ["shirt", "pants"],
        "sentiment": "disliked",
    }])}
    assert after[("shirt", "pants")]["compatibility_score"] < before[("shirt", "pants")]["compatibility_score"]
    assert after[("red", "pants")]["compatibility_score"] > after[("shirt", "pants")]["compatibility_score"]


def test_feedback_stays_with_current_wardrobe_and_preserves_style_preferences():
    wardrobe = [
        {"id": "classic", "name": "Classic shirt", "category": "top", "colour": "navy", "style": "classic"},
        {"id": "sport", "name": "Sport shirt", "category": "top", "colour": "navy", "style": "sporty"},
        {"id": "pants", "name": "Trousers", "category": "bottom", "colour": "cream"},
    ]
    unrelated = [{
        "product_id": "owned-outfit:old", "wardrobe_item_ids": ["deleted", "pants"],
        "sentiment": "saved",
    }]
    expected = plan_outfits(wardrobe, preferred_style="classic")
    actual = plan_outfits(wardrobe, preferred_style="classic", feedback=unrelated)
    assert [(o["item_ids"], o["compatibility_score"]) for o in expected] == [
        (o["item_ids"], o["compatibility_score"]) for o in actual]
    assert actual[0]["item_ids"][0] == "classic"


def test_capsule_can_use_saved_outfit_feedback_when_choosing_between_tops():
    wardrobe = [
        {"id": "first", "name": "First shirt", "category": "top", "colour": "navy"},
        {"id": "second", "name": "Second shirt", "category": "top", "colour": "navy"},
        {"id": "pants", "name": "Pants", "category": "bottom", "colour": "cream"},
    ]
    feedback = [{
        "product_id": "owned-outfit:sample", "wardrobe_item_ids": ["second", "pants"],
        "sentiment": "saved",
    }]
    chosen = capsule_plan(wardrobe, max_items=2, feedback=feedback)
    assert {x["id"] for x in chosen["items"]} == {"second", "pants"}


def test_formal_outfits_rank_classic_shoes_above_sporty_shoes():
    wardrobe = [
        {"id": "top", "name": "Shirt", "category": "top", "colour": "navy", "style": "classic"},
        {"id": "bottom", "name": "Trousers", "category": "bottom", "colour": "cream", "style": "classic"},
        {"id": "trainers", "name": "Sporty shoes", "category": "shoes",
         "colour": "black", "style": "sporty"},
        {"id": "loafers", "name": "Classic shoes", "category": "shoes",
         "colour": "black", "style": "classic"},
    ]
    looks = plan_outfits(wardrobe, occasion="business", preferred_style="classic")
    assert looks[0]["item_ids"][2] == "loafers"
    assert any(look["item_ids"][2] == "trainers" for look in looks)


def test_later_uploaded_best_shoes_are_considered():
    wardrobe = [
        {"id": "top", "name": "Classic shirt", "category": "top", "style": "classic"},
        {"id": "bottom", "name": "Classic trousers", "category": "bottom", "style": "classic"},
    ]
    wardrobe.extend(
        {"id": f"shoe{i}", "name": f"Sporty shoe {i}", "category": "shoes",
         "style": "sporty"} for i in range(5))
    wardrobe.append({"id": "bestshoe", "name": "Classic shoes",
                     "category": "shoes", "style": "classic"})
    looks = plan_outfits(wardrobe, occasion="formal", preferred_style="classic")
    assert "bestshoe" in looks[0]["item_ids"]
    assert "bestshoe" in {look["item_ids"][2] for look in looks}
    assert len(looks) == 4  # Best four candidates, not first four uploads


def test_cold_weather_selects_matching_outerwear_instead_of_first_upload():
    wardrobe = [
        {"id": "top", "name": "Shirt", "category": "top",
         "colour": "navy", "style": "classic"},
        {"id": "bottom", "name": "Trousers", "category": "bottom",
         "colour": "cream", "style": "classic"},
        {"id": "wrong", "name": "Sport jacket", "category": "outerwear",
         "colour": "orange", "style": "sporty"},
        {"id": "right", "name": "Classic coat", "category": "outerwear",
         "colour": "navy", "style": "classic"},
    ]
    looks = plan_outfits(wardrobe, climate="cold", preferred_style="classic",
                         avoided_colours=["orange"])
    assert "right" in looks[0]["item_ids"]
    assert "wrong" not in looks[0]["item_ids"]


def test_patterns_and_accent_balance_influence_composition():
    from services.wardrobe_compatibility import score_owned_outfit
    top = {"id": "top", "name": "Printed top", "category": "top",
           "colour": "blue", "pattern": "striped"}
    patterned = {"id": "pattern", "name": "Pattern trousers", "category": "bottom",
                 "colour": "cream", "pattern": "checked"}
    plain = {"id": "plain", "name": "Plain trousers", "category": "bottom",
             "colour": "cream", "pattern": "solid"}
    two_patterns = score_owned_outfit([top, patterned])
    balanced = score_owned_outfit([top, plain])
    assert balanced["compatibility_score"] > two_patterns["compatibility_score"]
    assert "labelled patterns" in " ".join(two_patterns["compatibility_reasons"])


def test_style_scores_still_respect_preferred_colours_and_user_feedback():
    items = [
        {"id": "navy", "name": "Navy top", "category": "top", "colour": "navy", "style": "classic"},
        {"id": "red", "name": "Red top", "category": "top", "colour": "red", "style": "casual"},
        {"id": "bottom", "name": "Bottom", "category": "bottom", "colour": "cream"},
    ]
    looks = plan_outfits(items, preferred_style="classic",
                         avoided_colours=["red"], feedback=[{
        "product_id": "owned-outfit:test",
        "wardrobe_item_ids": ["red", "bottom"], "sentiment": "liked",
    }])
    assert looks[0]["item_ids"][0] == "navy"
