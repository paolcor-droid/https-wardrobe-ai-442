"""Catalogue outfit generation uses only eligible, source-backed women's product records."""
from services.supplier_outfit_combinations import build_supplier_outfits


def product(sku, category, colour, department="womens", image=True):
    return {
        "external_id":sku, "name":category+" "+sku, "category":category,
        "colour_names":[colour], "department":department,
        "source_verified":True, "image_url":"https://example.org/"+sku+".jpg" if image else None,
        "recommendation_score":60.0,"customer_price":None,"currency":"AUD",
    }


def test_womens_outfits_from_supplier_without_owned_wardrobe():
    products=[
        product("top-1","blouse","navy"), product("bottom-1","trousers","cream"),
        product("shoes-1","shoes","black"), product("dress-1","dress","beige"),
    ]
    outfits=build_supplier_outfits(products)
    assert outfits
    assert all(row["garments"] for row in outfits)
    assert all(not row["stock_verified_live"] for row in outfits)


def test_mens_or_unverified_catalogue_records_are_never_in_outfits():
    products=[
        product("mens","trousers","navy","mens"),
        product("unknown","blouse","navy",image=False),
        product("dress-1","dress","beige"),
        product("shoes","shoes","black"),
    ]
    outfits=build_supplier_outfits(products)
    assert outfits
    assert all(g["product_id"] not in {"mens","unknown"}
               for row in outfits for g in row["garments"])


def test_no_outfit_if_no_eligible_garment():
    assert build_supplier_outfits([])==[]


def test_monochrome_genuine_outfits_are_not_suppressed():
    products = [
        product("top-black", "blouse", "black"),
        product("pants-black", "trousers", "black"),
        product("shoe-black", "shoes", "black"),
    ]
    diagnostics = {}
    looks = build_supplier_outfits(products, diagnostics=diagnostics)
    assert looks
    assert any("Monochrome" in look["reason"] for look in looks)
    assert diagnostics["accepted"] > 0
    assert all(look["stock_verified_live"] is False for look in looks)


def test_missing_supplier_colour_is_not_fabricated():
    products = [
        product("navy-blouse", "blouse", "navy"),
        product("unlabelled-trousers", "trousers", ""),
        product("black-shoes", "shoes", "black"),
    ]
    diagnostics = {}
    looks = build_supplier_outfits(products, diagnostics=diagnostics)
    assert looks
    assert diagnostics["missing_colour"] > 0
    assert any(any(not label for garment in look["garments"]
                   for label in garment["colour_names"]) for look in looks)
    assert "missing" in looks[0]["reason"].casefold()


def test_supplier_candidate_diagnostics_do_not_include_customer_data():
    diagnostics = {}
    assert build_supplier_outfits([], diagnostics=diagnostics) == []
    assert set(diagnostics) == {
        "repeated_or_duplicate", "missing_colour", "harmony", "accepted"
    }
    assert all(isinstance(value, int) for value in diagnostics.values())
