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
    assert ranked[0]["ranking_basis"] == "confirmed_wardrobe_labels_and_named_scan_swatches"
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
