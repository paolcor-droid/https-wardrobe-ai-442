from services.demo_outfit_presentation import style_copy, diversify_outfits

def test_title_mentions_real_shoe_accent():
    garments=[{"name":"T-shirt Heavy","category":"Tops"},{"name":"Chino trousers","category":"Bottoms"},{"name":"Loafers Penny","category":"Footwear"}]
    copy=style_copy(garments,["Navy","Navy","Camel"],"Casual")
    assert "Camel" in copy["title"] and "Penny Loafers" in copy["title"]
    assert "Navy" in copy["explanation"]
    assert "contrast" in copy["explanation"]

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
