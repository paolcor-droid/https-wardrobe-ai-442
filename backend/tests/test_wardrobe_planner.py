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
    assert len(outfits) == 2
    assert outfits[0]["item_ids"][-1] == "shoes1"
    assert outfits[1]["item_ids"][-1] == "shoes2"


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
