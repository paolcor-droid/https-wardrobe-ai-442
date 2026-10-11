"""End-to-end tests for the LUMIÈRE 4-stage review.

Stage 1 - Your Scan: upload -> skin-analysis -> profile persistence
Stage 2 - Discover: /catalogue/recommendations shape, pricing, no supplier leak
Stage 3 - Discover -> Try-On: prepare-tryon -> /tryon (ONE generation only)
Stage 4 - Regression (static): api.ts /api/upload still uses XMLHttpRequest
"""
import io
import os
import struct
import zlib
from pathlib import Path

import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

# Stage 1-3 make external calls; keep stage 4 static regression local.
LIVE_API_ENABLED = bool(BASE_URL)


# ---------- helpers ----------
def _png_bytes(width: int = 64, height: int = 64, rgb=(214, 174, 142)) -> bytes:
    """Synthesize a minimal valid solid-colour PNG (skin-tone-ish)."""
    def chunk(ctype: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + ctype
            + data
            + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
        )
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b""
    row = b"\x00" + bytes(rgb) * width
    for _ in range(height):
        raw += row
    idat = zlib.compress(raw, 9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


@pytest.fixture(scope="session")
def api_client():
    s = requests.Session()
    return s


@pytest.fixture(scope="session")
def selfie_path(api_client) -> str:
    data = _png_bytes()
    files = {"file": ("selfie.png", io.BytesIO(data), "image/png")}
    r = api_client.post(f"{API}/upload", files=files, timeout=60)
    assert r.status_code == 200, r.text
    path = r.json()["path"]
    assert isinstance(path, str) and path
    return path


# ============================================================
# STAGE 1 — Your Scan
# ============================================================
@pytest.mark.skipif(not LIVE_API_ENABLED, reason="Set EXPO_PUBLIC_BACKEND_URL for live API tests")
class TestStage1YourScan:
    def test_01_upload_selfie(self, selfie_path):
        assert selfie_path.endswith(".png")

    def test_02_skin_analysis_runs_and_returns_full_schema(self, api_client, selfie_path):
        r = api_client.post(f"{API}/skin-analysis", json={"image_path": selfie_path}, timeout=180)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("undertone", "depth", "chroma", "contrast", "season",
                  "palette", "best_neutrals", "best_accents",
                  "statement_colours", "caution_colours", "analysis_quality"):
            assert k in data, f"missing field {k}"
        assert data["undertone"] in {"warm", "neutral_warm", "neutral", "neutral_cool", "cool"}
        assert isinstance(data["best_neutrals"], list) and len(data["best_neutrals"]) > 0
        assert isinstance(data["best_accents"], list) and len(data["best_accents"]) > 0
        for sw in data["best_neutrals"] + data["best_accents"]:
            assert "name" in sw and "hex" in sw
        assert data["analysis_quality"]["confidence"] in {"low", "medium", "high"}

    def test_03_profile_persists_scan(self, api_client, selfie_path):
        # requires test_02 to have run just before
        r = api_client.get(f"{API}/profile", timeout=30)
        assert r.status_code == 200, r.text
        prof = r.json()
        assert prof["skin"], "profile.skin not persisted"
        assert prof["skin"]["image_path"] == selfie_path
        assert prof["skin"]["analyzed_at"]
        assert len(prof["skin"]["best_neutrals"]) > 0
        assert len(prof["skin"]["best_accents"]) > 0

    def test_04_preferred_and_avoided_colours_mutually_exclusive(self, api_client):
        payload = {
            "preferences": {
                "budget_min": 0, "budget_max": 500, "occasion": "casual",
                "categories": [], "climate": "mild", "style": "classic",
                "preferred_fit": "regular",
                "preferred_colours": ["navy", "ivory", "forest"],
                "avoided_colours": ["navy", "mustard"],
                "preferred_retailers": ["zara"],
            }
        }
        # Backend must reject a colour that is both preferred and avoided.
        r = api_client.put(f"{API}/profile", json=payload, timeout=30)
        assert r.status_code == 400, r.text
        assert "navy" in r.json().get("detail", "")
        # Confirm the conflicting state did not persist.
        prof = api_client.get(f"{API}/profile", timeout=30).json()
        prefs = prof["preferences"]
        overlap = set(prefs["preferred_colours"]) & set(prefs["avoided_colours"])
        assert not overlap, f"Conflicting colours persisted: {overlap}"
        # A non-conflicting save still succeeds.
        r2 = api_client.put(
            f"{API}/profile",
            json={"preferences": {**payload["preferences"],
                                  "preferred_colours": ["navy", "ivory", "forest"],
                                  "avoided_colours": ["mustard"]}},
            timeout=30,
        )
        assert r2.status_code == 200, r2.text
        prefs2 = r2.json()["preferences"]
        assert not (set(prefs2["preferred_colours"]) & set(prefs2["avoided_colours"]))


# ============================================================
# STAGE 2 — Discover (catalogue recommendations)
# ============================================================
@pytest.mark.skipif(not LIVE_API_ENABLED, reason="Set EXPO_PUBLIC_BACKEND_URL for live API tests")
class TestStage2Discover:
    @pytest.fixture(scope="class")
    def recs_payload(self, api_client):
        r = api_client.get(f"{API}/catalogue/recommendations", timeout=60)
        assert r.status_code == 200, r.text
        return r.json()

    def test_source_and_live_flag(self, recs_payload):
        assert recs_payload["source"] == "matterhorn_xml_trial_snapshot"
        assert recs_payload["live_inventory_enabled"] is False
        # notice must not describe stock as live
        notice = (recs_payload.get("notice") or "").lower()
        assert "live" not in notice or "not" in notice

    def test_recommendations_shape(self, recs_payload):
        recs = recs_payload["recommendations"]
        assert isinstance(recs, list) and len(recs) > 0
        for rec in recs:
            for k in ("product_id", "name", "brand", "image_url",
                      "colour_names", "sizes", "materials",
                      "recommendation_reasons"):
                assert k in rec, f"missing field: {k}"
            assert rec["image_url"], f"empty image_url for {rec.get('product_id')}"
            assert rec["name"]
            assert rec["brand"]
            assert isinstance(rec["recommendation_reasons"], list)
            assert len(rec["recommendation_reasons"]) > 0, f"empty reasons for {rec['product_id']}"

    def test_no_supplier_metadata_leak(self, recs_payload):
        forbidden = {"provider_id", "provider_kind", "source_url", "availability",
                     "supplier_cost", "wholesale_cost", "customer_price"}
        for rec in recs_payload["recommendations"]:
            leaked = forbidden.intersection(rec.keys())
            assert not leaked, f"leaked fields {leaked} on {rec.get('product_id')}"

    def test_111506_pricing_is_16_13(self, recs_payload):
        """Supplier 12.90 + 25% markup must equal 16.13 exactly."""
        rec = next((r for r in recs_payload["recommendations"]
                    if r["product_id"] == "111506"), None)
        assert rec is not None, "product_id 111506 missing from recommendations"
        assert rec["price"] == 16.13, f"expected 16.13, got {rec['price']}"

    def test_reasons_reference_personalization(self, recs_payload):
        joined = " ".join(
            " ".join(r["recommendation_reasons"]).lower()
            for r in recs_payload["recommendations"]
        )
        # at least one of these personalization axes must be mentioned somewhere
        assert any(tok in joined for tok in
                   ("colour", "color", "palette", "style", "climate", "occasion",
                    "fit", "neutral", "accent", "undertone", "season"))


# ============================================================
# STAGE 3 — Discover -> Try-On (ONE generation only)
# ============================================================
@pytest.mark.skipif(not LIVE_API_ENABLED, reason="Set EXPO_PUBLIC_BACKEND_URL for live API tests")
class TestStage3TryOn:
    def test_prepare_tryon_for_111506(self, api_client):
        r = api_client.post(f"{API}/catalogue/products/111506/prepare-tryon", timeout=120)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["path"]
        assert body["name"]
        # The supplier URL must never be exposed in the customer handoff.
        assert "preview_url" not in body
        assert "matterhorn" not in r.text.lower()
        pytest.garment_path = body["path"]  # type: ignore[attr-defined]

    def test_prepare_tryon_unknown_product_404(self, api_client):
        r = api_client.post(f"{API}/catalogue/products/DOES_NOT_EXIST/prepare-tryon", timeout=30)
        assert r.status_code == 404

    def test_upload_person_photo(self, api_client):
        data = _png_bytes(96, 128, rgb=(190, 160, 130))
        files = {"file": ("me.png", io.BytesIO(data), "image/png")}
        r = api_client.post(f"{API}/upload", files=files, timeout=60)
        assert r.status_code == 200, r.text
        pytest.person_path = r.json()["path"]  # type: ignore[attr-defined]

    def test_tryon_one_generation_and_persist(self, api_client):
        person = getattr(pytest, "person_path", None)
        garment = getattr(pytest, "garment_path", None)
        assert person and garment, "prerequisite upload tests did not run"
        r = api_client.post(
            f"{API}/tryon",
            json={"person_image_path": person, "garment_image_path": garment},
            timeout=240,
        )
        assert r.status_code == 200, r.text
        tryon = r.json()
        assert tryon["result_path"]
        assert tryon["person_image_path"] == person
        assert tryon["garment_image_path"] == garment
        pytest.tryon_id = tryon["id"]  # type: ignore[attr-defined]

        # verify result image is retrievable
        rf = api_client.get(f"{API}/files/{tryon['result_path']}", timeout=60)
        assert rf.status_code == 200
        assert rf.headers.get("Content-Type", "").startswith("image/")

        # verify persisted in /tryons list
        rl = api_client.get(f"{API}/tryons", timeout=30)
        assert rl.status_code == 200
        ids = [t["id"] for t in rl.json()]
        assert tryon["id"] in ids


# ============================================================
# STAGE 4 — Regression (static code check on api.ts)
# ============================================================
class TestStage4XhrRegression:
    def test_uploadImage_still_uses_xhr(self):
        src = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "api.ts").read_text()
        # must use XMLHttpRequest for /api/upload
        idx = src.find("uploadImage")
        assert idx > 0, "uploadImage not found"
        snippet = src[idx: idx + 2500]
        assert "XMLHttpRequest" in snippet, "uploadImage no longer uses XMLHttpRequest"
        assert 'xhr.open("POST"' in snippet and "/api/upload" in snippet, \
            "XHR POST to /api/upload missing"
        # explanatory comment about WinterCG FormData issue should still be there
        assert "WinterCG" in snippet or "Unsupported FormDataPart" in snippet, \
            "regression comment removed"
