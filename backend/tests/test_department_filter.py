"""Focused tests for the shop_for department hard filter and genuine men's snapshot."""
from services.catalogue_providers import normalize_product, derive_department
from services.matterhorn_trial_snapshot import MATTERHORN_TRIAL_SNAPSHOT
from services.product_recommendations import rank_verified_products, customer_recommendations

FIGL_WOMENS = {"111506", "135767", "150432", "8411"}


def _profile(shop_for):
    return {"preferences": {"budget_min": 0, "budget_max": 500, "shop_for": shop_for}}


def _normalized():
    return [normalize_product("matterhorn", raw) for raw in MATTERHORN_TRIAL_SNAPSHOT]


def test_department_derived_from_genuine_category_path():
    assert derive_department("/MEN/Men`s Underwear/T-Shirts") == "mens"
    assert derive_department("/WOMEN/Women`s Lingerie/Bras") == "womens"
    # "WOMEN`S" must never be misread as men's.
    assert derive_department("/WOMEN`S COATS, JACKETS/Parkas") == "womens"
    assert derive_department("/DRESSES/Evening") == "womens"
    assert derive_department(None) == "unisex"
    assert derive_department("/UNISEX/Accessories/Scarves") == "unisex"


def test_snapshot_departments_are_consistent_with_source():
    by_id = {r["external_id"]: r["department"] for r in MATTERHORN_TRIAL_SNAPSHOT}
    for fid in FIGL_WOMENS:
        assert by_id[fid] == "womens"
    assert by_id["113679"] == "mens"


def test_mens_never_returns_womens():
    ranked = rank_verified_products(_normalized(), _profile("mens"), limit=50)
    assert ranked, "men's preference should return genuine men's products"
    assert all(p["department"] == "mens" for p in ranked)
    ids = {p["external_id"] for p in ranked}
    assert not (FIGL_WOMENS & ids), "women's Figl products must not appear for Men"


def test_womens_never_returns_mens():
    ranked = rank_verified_products(_normalized(), _profile("womens"), limit=50)
    assert ranked
    assert all(p["department"] == "womens" for p in ranked)
    assert FIGL_WOMENS <= {p["external_id"] for p in ranked}


def test_all_returns_both_departments():
    ranked = rank_verified_products(_normalized(), _profile("all"), limit=50)
    depts = {p["department"] for p in ranked}
    assert {"mens", "womens"} <= depts


def test_genuine_unisex_allowed_for_either_preference():
    unisex_raw = {
        "external_id": "UNI-1",
        "name": "Unisex Scarf",
        "category": "Accessories",
        "category_path": "/UNISEX/Accessories/Scarves",
        "price": 10.0,
        "currency": "AUD",
        "colour_names": ["grey"],
        "sizes": ["OS"],
        "availability": "5",
    }
    products = _normalized() + [normalize_product("matterhorn", unisex_raw)]
    for pref in ("mens", "womens"):
        ids = {p["external_id"] for p in rank_verified_products(products, _profile(pref), limit=50)}
        assert "UNI-1" in ids, f"genuine unisex should show for {pref}"


def test_customer_payload_hides_department_and_supplier_metadata():
    ranked = rank_verified_products(_normalized(), _profile("mens"), limit=50)
    for item in customer_recommendations(ranked):
        for hidden in ("department", "provider_id", "provider_kind", "source_url", "availability"):
            assert hidden not in item


def test_mens_pricing_is_supplier_times_1_25():
    ranked = rank_verified_products(_normalized(), _profile("mens"), limit=50)
    by_id = {p["product_id"]: p for p in customer_recommendations(ranked)}
    # Pierre Cardin T-shirt genuine supplier price 8.90 -> 8.90 * 1.25 = 11.13 (HALF_UP).
    assert by_id["113679"]["price"] == 11.13
