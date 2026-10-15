import pytest
from services.shopify_test_adapter import shopify_test_readiness, create_checkout


def test_shopify_checkout_is_always_disabled(monkeypatch):
    monkeypatch.setenv("LUMIERE_SHOPIFY_TEST_MODE", "1")
    monkeypatch.setenv("LUMIERE_SHOPIFY_TEST_STORE_DOMAIN", "test-store.myshopify.com")
    state = shopify_test_readiness()
    assert state["configured"] is True
    assert state["checkout_enabled"] is False
    assert state["payment_enabled"] is False
    assert state["order_submission_enabled"] is False
    with pytest.raises(RuntimeError, match="disabled"):
        create_checkout("synthetic-item")


def test_shopify_invalid_store_does_not_activate(monkeypatch):
    monkeypatch.setenv("LUMIERE_SHOPIFY_TEST_MODE", "1")
    monkeypatch.setenv("LUMIERE_SHOPIFY_TEST_STORE_DOMAIN", "example.org")
    assert shopify_test_readiness()["configured"] is False
