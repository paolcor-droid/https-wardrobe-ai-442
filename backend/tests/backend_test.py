"""Backend API tests for Lumière shopping app (skin analysis, products, wishlist, tryon)."""
import os
import base64
import pytest
import requests
from pathlib import Path

# Read backend URL from frontend .env
FRONTEND_ENV = Path("/app/frontend/.env").read_text()
BASE_URL = next(l.split("=", 1)[1].strip() for l in FRONTEND_ENV.splitlines() if l.startswith("EXPO_PUBLIC_BACKEND_URL="))
API = f"{BASE_URL.rstrip('/')}/api"


@pytest.fixture(scope="module")
def face_image_b64():
    """Fetch a small real portrait image and return base64."""
    url = "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=300"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return base64.b64encode(r.content).decode()


@pytest.fixture(scope="module")
def body_image_b64():
    url = "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=400"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return base64.b64encode(r.content).decode()


# ============= Products =============
class TestProducts:
    def test_list_products_returns_seeded(self):
        r = requests.get(f"{API}/products", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 30, f"Expected >=30 seeded products, got {len(data)}"
        p = data[0]
        for k in ["id", "name", "brand", "category", "price", "image_url", "palette_tags"]:
            assert k in p, f"missing field {k}"

    def test_list_products_category_filter(self):
        r = requests.get(f"{API}/products", params={"category": "tops"}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert len(data) > 0
        assert all(p["category"] == "tops" for p in data)

    def test_get_product_by_id(self):
        listing = requests.get(f"{API}/products", timeout=15).json()
        pid = listing[0]["id"]
        r = requests.get(f"{API}/products/{pid}", timeout=15)
        assert r.status_code == 200
        assert r.json()["id"] == pid

    def test_get_product_404(self):
        r = requests.get(f"{API}/products/nonexistent-id", timeout=15)
        assert r.status_code == 404


# ============= Profile =============
class TestProfile:
    def test_profile_persistence(self):
        payload = {
            "preferences": {"budget_min": 50, "budget_max": 300, "occasion": "work", "categories": ["tops", "shoes"]},
            "skin_tone": {"undertone": "warm", "season": "autumn",
                          "palette": ["#8B4513", "#D2691E", "#CD853F", "#DEB887", "#F4A460", "#A0522D"],
                          "description": "Warm autumn tones."},
        }
        r = requests.post(f"{API}/profile", json=payload, timeout=15)
        assert r.status_code == 200
        r2 = requests.get(f"{API}/profile", timeout=15)
        assert r2.status_code == 200
        data = r2.json()
        assert data["preferences"]["occasion"] == "work"
        assert data["skin_tone"]["undertone"] == "warm"
        assert len(data["skin_tone"]["palette"]) == 6


# ============= Wishlist =============
class TestWishlist:
    def test_wishlist_toggle_and_get(self):
        listing = requests.get(f"{API}/products", timeout=15).json()
        pid = listing[0]["id"]
        # Ensure clean state - toggle to remove if present
        current = requests.get(f"{API}/wishlist", timeout=15).json()
        if any(p["id"] == pid for p in current):
            requests.post(f"{API}/wishlist/{pid}", timeout=15)
        # Add
        r = requests.post(f"{API}/wishlist/{pid}", timeout=15)
        assert r.status_code == 200
        assert r.json()["action"] == "added"
        wl = requests.get(f"{API}/wishlist", timeout=15).json()
        assert any(p["id"] == pid for p in wl)
        assert "name" in wl[0]  # full product objects
        # Remove
        r2 = requests.post(f"{API}/wishlist/{pid}", timeout=15)
        assert r2.json()["action"] == "removed"


# ============= Skin Analysis (Gemini 3 Flash) =============
class TestSkinAnalyze:
    def test_skin_analyze(self, face_image_b64):
        r = requests.post(f"{API}/skin/analyze", json={"face_photo": face_image_b64}, timeout=90)
        assert r.status_code == 200, f"skin analyze failed: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert data["undertone"] in ["warm", "cool", "neutral"]
        assert data["season"] in ["spring", "summer", "autumn", "winter"]
        assert isinstance(data["palette"], list) and len(data["palette"]) == 6
        assert all(c.startswith("#") for c in data["palette"])
        assert isinstance(data["description"], str) and len(data["description"]) > 5


# ============= Try-On (Nano Banana) =============
class TestTryOn:
    def test_tryon_generate_and_history(self, body_image_b64):
        listing = requests.get(f"{API}/products", timeout=15).json()
        pid = listing[0]["id"]
        r = requests.post(f"{API}/tryon", json={"product_id": pid, "body_photo": body_image_b64}, timeout=120)
        assert r.status_code == 200, f"tryon failed: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert "generated_image" in data and len(data["generated_image"]) > 100
        assert data["product_id"] == pid
        # History
        hist = requests.get(f"{API}/tryon", timeout=15).json()
        assert isinstance(hist, list) and len(hist) >= 1
        assert any(t["id"] == data["id"] for t in hist)
