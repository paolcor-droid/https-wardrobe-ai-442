"""End-to-end tests over the public API for the shop_for department filter."""
import os
import io
import struct
import zlib
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL")
BASE_URL = (BASE_URL or "https://style-scan-v3.preview.emergentagent.com").rstrip("/")

FIGL_WOMENS = {"111506", "135767", "150432", "8411"}
MENS_IDS = {
    "113679", "116218", "157060", "116219", "116327",
    "181810", "118360", "181797", "211659", "230084",
}
HIDDEN_KEYS = ("department", "provider_id", "provider_kind", "source_url", "availability",
               "supplier_cost", "wholesale_cost", "customer_price")


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    yield s
    # Reset profile at end
    try:
        s.put(f"{BASE_URL}/api/profile", json={"preferences": {"shop_for": "all"}}, timeout=30)
    except Exception:
        pass


def _set_shop_for(api, value):
    r = api.put(f"{BASE_URL}/api/profile", json={"preferences": {"shop_for": value}}, timeout=30)
    assert r.status_code == 200, f"PUT /api/profile shop_for={value} -> {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("preferences", {}).get("shop_for") == value
    return body


def _get_recs(api):
    r = api.get(f"{BASE_URL}/api/catalogue/recommendations", timeout=60)
    assert r.status_code == 200, f"GET recs -> {r.status_code}: {r.text}"
    data = r.json()
    assert "recommendations" in data
    return data


# ---------- Department filter core ----------
def test_mens_only_returns_mens(api):
    _set_shop_for(api, "mens")
    data = _get_recs(api)
    items = data["recommendations"]
    assert items, "mens preference must return at least one product"
    ids = {it["product_id"] for it in items}
    assert ids.isdisjoint(FIGL_WOMENS), f"Women's Figl must not appear for mens; found {ids & FIGL_WOMENS}"
    # at least some genuine men's IDs should appear
    assert ids & MENS_IDS, f"Expected men's IDs; got {ids}"
    print(f"MENS saw IDs: {sorted(ids)}")


def test_womens_only_returns_womens(api):
    _set_shop_for(api, "womens")
    data = _get_recs(api)
    ids = {it["product_id"] for it in data["recommendations"]}
    assert ids.isdisjoint(MENS_IDS), f"Men's must not appear for womens; found {ids & MENS_IDS}"
    # All returned items must be from the women's Figl set (no men's leak).
    # Note: not every Figl ID will appear — palette/avoid-colour filters may legitimately drop some.
    assert ids <= FIGL_WOMENS, f"Non-women's product leaked for womens pref: {ids - FIGL_WOMENS}"
    assert ids, "At least one women's product should appear"


def test_all_returns_both(api):
    _set_shop_for(api, "all")
    data = _get_recs(api)
    ids = {it["product_id"] for it in data["recommendations"]}
    assert ids & FIGL_WOMENS, "all should include women's"
    assert ids & MENS_IDS, "all should include men's"


# ---------- Pricing ----------
def test_mens_pricing_markup(api):
    _set_shop_for(api, "mens")
    data = _get_recs(api)
    by_id = {it["product_id"]: it for it in data["recommendations"]}
    assert "113679" in by_id, "Pierre Cardin 113679 should appear for mens"
    assert by_id["113679"]["price"] == 11.13, by_id["113679"].get("price")


def test_womens_pricing_markup(api):
    _set_shop_for(api, "womens")
    data = _get_recs(api)
    by_id = {it["product_id"]: it for it in data["recommendations"]}
    assert "111506" in by_id
    assert by_id["111506"]["price"] == 16.13


# ---------- Metadata leak ----------
def test_no_metadata_leak(api):
    _set_shop_for(api, "mens")
    data = _get_recs(api)
    for it in data["recommendations"]:
        for k in HIDDEN_KEYS:
            assert k not in it, f"forbidden key '{k}' present in product {it.get('product_id')}: {it}"


# ---------- Fields present + reasons ----------
def test_mens_products_full_payload(api):
    _set_shop_for(api, "mens")
    data = _get_recs(api)
    items = data["recommendations"]
    required = ("product_id", "name", "brand", "image_url", "colour_names",
                "sizes", "materials", "recommendation_reasons", "price")
    for it in items:
        for k in required:
            assert k in it, f"missing {k} in {it}"
        assert it["recommendation_reasons"], f"empty reasons on {it['product_id']}"


# ---------- Ranking signals ----------
def test_budget_filter_still_applies(api):
    r = api.put(f"{BASE_URL}/api/profile",
                json={"preferences": {"shop_for": "all", "budget_min": 0, "budget_max": 15}},
                timeout=30)
    assert r.status_code == 200
    data = _get_recs(api)
    for it in data["recommendations"]:
        assert it["price"] <= 15 + 0.01, f"over-budget item {it['product_id']} price={it['price']}"
    # reset
    api.put(f"{BASE_URL}/api/profile",
            json={"preferences": {"shop_for": "all", "budget_min": 0, "budget_max": 500}},
            timeout=30)


# ---------- Prepare try-on hides matterhorn ----------
def test_prepare_tryon_mens_no_matterhorn(api):
    r = api.post(f"{BASE_URL}/api/catalogue/products/113679/prepare-tryon", timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "preview_url" not in body, f"preview_url must be absent; got {body}"
    blob = str(body).lower()
    assert "matterhorn" not in blob, f"matterhorn leaked in prepare-tryon: {body}"
    assert body.get("stored_path") or body.get("path") or body.get("garment_path"), f"no stored path: {body}"
    assert body.get("name")


# ---------- Prior fix regression: colour conflict ----------
def test_profile_colour_conflict_rejected(api):
    r = api.put(f"{BASE_URL}/api/profile",
                json={"preferences": {"preferred_colours": ["red"], "avoided_colours": ["red"]}},
                timeout=30)
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
    # verify not persisted - should not have 'red' in both
    g = api.get(f"{BASE_URL}/api/profile", timeout=30).json()
    prefs = g.get("preferences", {})
    both = set(prefs.get("preferred_colours") or []) & set(prefs.get("avoided_colours") or [])
    assert "red" not in both


# ---------- One try-on generation ----------
def _png_bytes(color=(180, 140, 110)):
    """Synthesise a tiny solid-colour PNG."""
    w = h = 64
    raw = b"".join(bytes([0]) + bytes(color) * w for _ in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw, 9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def test_one_mens_tryon_e2e(api):
    # prepare garment
    r = api.post(f"{BASE_URL}/api/catalogue/products/113679/prepare-tryon", timeout=60)
    assert r.status_code == 200
    garment = r.json()
    garment_path = garment.get("stored_path") or garment.get("path") or garment.get("garment_path")
    assert garment_path

    # upload person photo
    files = {"file": ("person.png", io.BytesIO(_png_bytes((220, 180, 150))), "image/png")}
    rs = requests.Session()
    up = rs.post(f"{BASE_URL}/api/upload", files=files, timeout=60)
    assert up.status_code == 200, up.text
    person_path = up.json().get("path") or up.json().get("stored_path")
    assert person_path

    # one tryon
    payload = {"person_image_path": person_path, "garment_image_path": garment_path}
    gen = api.post(f"{BASE_URL}/api/tryon", json=payload, timeout=180)
    assert gen.status_code == 200, gen.text
    out = gen.json()
    result_path = out.get("result_path") or out.get("image_path") or out.get("path")
    assert result_path, f"no result image path in response: {out}"

    # Listed by GET /api/tryons
    lst = api.get(f"{BASE_URL}/api/tryons", timeout=30)
    assert lst.status_code == 200
    body = lst.json()
    rows = body if isinstance(body, list) else body.get("tryons") or body.get("items") or []
    assert any((r.get("result_path") or r.get("image_path") or r.get("path")) == result_path for r in rows), \
        f"result not in tryons list: {rows[:3]}"
