from services.catalogue_providers import list_providers, normalize_product


def test_provider_directory_includes_romanelli_without_fake_live_access():
    providers = {p["id"]: p for p in list_providers()}
    assert "romanelli-b2b" in providers
    assert providers["romanelli-b2b"]["kind"] == "wholesale"
    assert providers["romanelli-b2b"]["supports_live_catalogue"] is False


def test_normalizer_requires_source_backing():
    try:
        normalize_product("test", {"name": "Unverified shirt"})
        assert False, "unverified products must be rejected"
    except ValueError:
        pass


def test_normalizer_preserves_verified_source_url():
    item = normalize_product("test", {
        "external_id": "abc", "name": "Verified shirt",
        "source_url": "https://example.com/product/abc", "price": 99,
    })
    assert item["live"] is True
    assert item["source_url"].endswith("/abc")
