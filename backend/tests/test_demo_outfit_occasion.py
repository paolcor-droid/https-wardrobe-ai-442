from services.demo_outfit_occasion import infer_occasion
from services.demo_outfit_presentation import diversify_outfits

def part(name, category, colour="Navy"):
    return {"name":name,"category":category,"colour_names":[colour],"price":50}

def test_smart_casual_requires_more_than_a_casual_tee():
    look=[part("T-shirt Heavy","Tops"),part("Chino trousers","Bottoms"),part("Penny loafers","Footwear")]
    assert infer_occasion(look) == "Smart casual"

def test_business_requires_jacket_and_complementary_garments():
    look=[part("Classic shirt","Tops"),part("Tailored trousers","Bottoms"),part("Blazer","Outerwear")]
    assert infer_occasion(look) == "Business"

def test_formal_requires_strong_combination_evidence():
    look=[part("Formal suit jacket blazer","Outerwear"),part("Tailored trousers","Bottoms"),part("Oxford dress shoes","Footwear")]
    assert infer_occasion(look) == "Formal"
    assert infer_occasion([part("Blazer","Outerwear"),part("Shorts","Bottoms"),part("Sneakers","Footwear")]) != "Formal"

def test_evening_uses_explicit_dress_metadata():
    assert infer_occasion([part("Satin evening dress","Dresses"),part("Heels","Footwear")]) == "Evening"

def test_hot_casual_is_not_formal_from_weather_alone():
    assert infer_occasion([part("Linen tee","Tops"),part("Shorts","Bottoms"),part("Sneakers","Footwear")],"hot") == "Hot-weather casual"

def test_duplicate_look_signatures_excluded_despite_different_skus_and_prices():
    def outfit(code, top, price):
        return {"id":code,"title":code,"score":100-price/100,
                "garments":[part(top,"Tops"),part("Chino trousers","Bottoms"),part("Loafers Penny","Footwear","Camel")]}
    looks=[outfit("a","Cotton T-shirt",30),outfit("b","Premium T-shirt",80),outfit("c","Crew-neck Sweatshirt",50)]
    chosen=diversify_outfits(looks)
    assert {o["id"] for o in chosen}=={"a","c"}


def test_occasion_confidence_flags_borderline_smart_casual():
    from services.demo_outfit_occasion import occasion_assessment
    look=[part("T-shirt Heavy","Tops"),part("Chino trousers","Bottoms"),part("Penny loafers","Footwear")]
    result=occasion_assessment(look)
    assert result["occasion"] == "Smart casual"
    assert result["confidence"] == "Moderate"
    assert "Mixed" in result["evidence"]


def test_confidence_is_reduced_when_xml_disagrees():
    from services.demo_outfit_occasion import occasion_assessment
    look=[part("Classic shirt","Tops"),part("Tailored trousers","Bottoms"),part("Blazer","Outerwear")]
    strong=occasion_assessment(look)
    conflicting=occasion_assessment(look,source_occasion="Casual")
    assert strong["occasion"] == "Business"
    assert strong["confidence"] == "High"
    assert conflicting["confidence"] == "Moderate"
    assert "differs" in conflicting["evidence"]
