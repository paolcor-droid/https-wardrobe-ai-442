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
