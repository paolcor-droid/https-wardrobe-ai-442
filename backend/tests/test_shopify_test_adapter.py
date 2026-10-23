import pytest
from services.shopify_test_adapter import shopify_test_readiness, country_checkout_readiness, create_checkout


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


def test_country_checkout_is_fail_closed_for_both_launch_markets():
    for country in ("AU", "MD"):
        status = country_checkout_readiness(country)
        assert status["country"] == country
        assert status["checkout_enabled"] is False
        assert status["payment_enabled"] is False
        assert status["orders_enabled"] is False
        assert status["required_checks"]
    with pytest.raises(ValueError):
        country_checkout_readiness("US")


def test_supplier_live_readiness_never_implies_live_stock():
    from services.supplier_catalogue_store import live_supplier_readiness
    for provider in ("matterhorn", "vaitto", "romanelli-b2b", "brandsdistribution"):
        readiness = live_supplier_readiness(provider)
        assert readiness["live_price_enabled"] is False
        assert readiness["live_stock_enabled"] is False
        assert readiness["order_routing_enabled"] is False
    with pytest.raises(ValueError):
        live_supplier_readiness("zara")


@pytest.mark.parametrize("untrusted_domain", [
    "evil.myshopify.com.attacker.com", "test.myshopify.com/path",
    "test.myshopify.com:443", "test.myshopify.com?token=abc",
    "https://test.myshopify.com", "test.myshopify.com@evil.test",
])
def test_untrusted_shopify_domains_never_enable_checkout(monkeypatch, untrusted_domain):
    monkeypatch.setenv("LUMIERE_SHOPIFY_TEST_MODE", "1")
    monkeypatch.setenv("LUMIERE_SHOPIFY_TEST_STORE_DOMAIN", untrusted_domain)
    state = shopify_test_readiness()
    assert state["checkout_enabled"] is False
    assert state["payment_enabled"] is False
    assert state["order_submission_enabled"] is False
    with pytest.raises(RuntimeError, match="disabled"):
        create_checkout()
