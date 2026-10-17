from services.demo_outfit_presentation import style_copy, diversify_outfits

def test_title_mentions_real_shoe_accent():
    garments=[{"name":"T-shirt Heavy","category":"Tops"},{"name":"Chino trousers","category":"Bottoms"},{"name":"Loafers Penny","category":"Footwear"}]
    copy=style_copy(garments,["Navy","Navy","Camel"],"Casual")
    assert "Camel Loafers Penny" in copy["title"] and "Navy Chino trousers" in copy["title"]
    assert "Navy" in copy["explanation"]
    assert "illustrative" in copy["explanation"]

def test_monochrome_copy_does_not_claim_unseen_accent():
    garments=[{"name":"Shirt","category":"Tops"},{"name":"Trousers","category":"Bottoms"}]
    copy=style_copy(garments,["Navy","Navy"],"Work")
    assert "consistent" in copy["explanation"]
    assert "Camel" not in str(copy)

def test_diversifier_still_returns_existing_complete_cards():
    def card(name, colours, score):
        return {"id":name,"score":score,"garments":[{"name":"Shirt","category":"Tops","colour_names":[colours[0]]},{"name":"Trousers","category":"Bottoms","colour_names":[colours[1]]}]}
    src=[card("a",["Navy","Navy"],95),card("b",["Navy","Navy"],94),card("c",["Olive","Beige"],93)]
    result=diversify_outfits(src,3)
    assert [i["id"] for i in result]==["a","c"]
    assert len(result)==2


def test_monochrome_titles_describe_actual_garments():
    garments=[{"name":"Crew-neck T-shirt","category":"Tops"}, {"name":"Tailored trousers","category":"Bottoms"}, {"name":"Loafers","category":"Footwear"}]
    copy=style_copy(garments,["Navy","Navy","Navy"],"Smart casual")
    assert "Crew-neck T-shirt" in copy["title"]
    assert "Tailored trousers" in copy["title"]
    assert "coordinated look" not in copy["title"]


def test_palette_diversity_does_not_repeat_navy_and_camel_footwear():
    def look(id, top, bottom, shoes, score):
        return {"id": id, "score": score, "garments": [
            {"name": "T-shirt", "category": "Tops", "colour_names": [top]},
            {"name": "Chinos", "category": "Bottoms", "colour_names": [bottom]},
            {"name": "Penny loafers", "category": "Footwear", "colour_names": [shoes]},
        ]}
    result = diversify_outfits([
        look("a", "Navy", "Navy", "Camel", 90),
        look("b", "Navy", "Navy", "Camel", 88),
        look("c", "Olive", "Cream", "Brown", 86)], 10)
    assert [x["id"] for x in result] == ["a", "c"]


def test_collection_ranking_prefers_distinct_palette_when_scores_are_close():
    def outfit(code, colours, score, top):
        return {"id":code,"title":code,"score":score,"garments":[
            {"name":top,"category":"Tops","colour_names":[colours[0]]},
            {"name":"Chino trousers","category":"Bottoms","colour_names":[colours[1]]},
            {"name":"Loafers Penny","category":"Footwear","colour_names":[colours[2]]}]}
    chosen=diversify_outfits([
        outfit("a",["Navy","Navy","Camel"],100,"T-shirt"),
        outfit("b",["Navy","Camel","Navy"],99,"Sweatshirt"),
        outfit("c",["Olive","Cream","Brown"],93,"Linen shirt"),
    ],limit=3)
    assert chosen[0]["id"] == "a"
    assert chosen[1]["id"] == "c"


def test_outfit_title_names_all_three_selected_colours_and_pieces():
    look = [{"name": "Shirt Oxford"}, {"name": "Chino trousers"}, {"name": "Loafers Penny"}]
    title = style_copy(look, ["White", "Cream", "Navy"], "Smart casual")["title"]
    assert title == "Smart casual: White Shirt Oxford, Cream Chino trousers and Navy Loafers Penny"
