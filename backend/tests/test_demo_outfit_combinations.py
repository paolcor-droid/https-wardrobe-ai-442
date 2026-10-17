"""Generated demo looks never bypass stock-backed eligibility and colour choices."""
from services.demo_outfit_combinations import garment_role, harmony, make_generated_outfits

def item(sku, name, colour, category, department="mens", season="Primavera/Estate"):
    return {"external_id":sku,"name":name,"category":category,"department":department,
            "season":season,"colour_names":[colour],"price":40,"materials":["Cotton 100%"],
            "recommendation_score":75}

def test_role_detection_and_colour_harmony():
    assert garment_role(item("1","Canvas sneakers","Navy","Footwear")) == "shoes"
    assert garment_role(item("2","Chino trousers","Navy","Trousers")) == "bottom"
    assert harmony(["Navy","Beige","Olive"])[0] > harmony(["Red","Cobalt Blue","Mustard"])[0]

def test_generated_complete_outfits_respect_eligible_colours_and_season():
    products = [item("a","Linen shirt","Navy","Tops"),
                item("b","Chino trousers","Beige","Trousers"),
                item("c","Canvas sneakers","Navy","Footwear")]
    profile={"preferences":{"preferred_colours":["Navy","Beige"],"avoided_colours":["Black"],"climate":"hot"}}
    result=make_generated_outfits(products,profile)
    assert len(result)==1
    outfit=result[0]
    assert outfit["origin"]=="generated"
    assert outfit["occasion"]=="Hot-weather casual"
    assert len(outfit["garments"])==3
    assert "New" not in outfit["id"]
    assert outfit["total_price"]==120
    assert "Black" not in str(outfit["garments"])

def test_no_incomplete_or_avoided_colour_or_mixed_department():
    base=[item("a","Shirt","Navy","Tops"),item("b","Trousers","Beige","Trousers")]
    prefs={"preferences":{"preferred_colours":["Navy","Beige"],"avoided_colours":["Black"]}}
    assert make_generated_outfits(base,prefs)==[]
    assert make_generated_outfits(base+[item("c","Shoes","Black","Footwear")],prefs)==[]
    assert make_generated_outfits(base+[item("c","Shoes","Navy","Footwear","womens")],prefs)==[]


def test_tonal_compatibility_rewards_light_dark_balance():
    balanced, explanation = harmony(["White", "Cream", "Navy"])
    flat, _ = harmony(["Navy", "Navy", "Navy"])
    assert balanced > flat
    assert "tonal contrast" in explanation


def test_two_accent_families_are_not_automatically_rewarded():
    restrained, _ = harmony(["Navy", "Cream", "Camel"])
    busy, _ = harmony(["Navy", "Coral", "Olive", "Cobalt Blue"])
    assert restrained > busy
