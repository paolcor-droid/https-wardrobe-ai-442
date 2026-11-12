"""Wardrobe audience filtering must not repurpose old men's garments when the fashion profile changes."""
from services.wardrobe_planner import plan_outfits
from services.wardrobe_mixed_outfits import mixed_outfits

def _item(item_id, category, audience=None):
    row = {"id":item_id, "name":f"{item_id} garment", "category":category,
           "colour":"Navy", "style":"casual"}
    if audience is not None:
        row["shop_for"]=audience
    return row

def test_womens_planner_does_not_use_mens_or_legacy_untagged():
    items=[_item("mens-shirt","top","mens"),_item("mens-trousers","bottom","mens"),
           _item("legacy-shirt","top"),_item("legacy-trousers","bottom")]
    assert plan_outfits(items,shop_for="womens")==[]

def test_womens_planner_uses_womens_and_explicit_unisex():
    items=[_item("womens-top","top","womens"),_item("everyone-trousers","bottom","all"),
           _item("mens-top","top","mens")]
    outfits=plan_outfits(items,shop_for="womens")
    assert outfits
    for outfit in outfits:
        assert "mens-top" not in outfit["item_ids"]
        assert "womens-top" in outfit["item_ids"]

def test_womens_mixed_planner_blocks_old_male_wardrobe():
    items=[_item("mens-top","top","mens"),_item("mens-bottom","bottom","mens"),
           _item("legacy-top","top")]
    result=mixed_outfits(items,[],preferences={"shop_for":"womens"})
    assert result["outfits"]==[]
