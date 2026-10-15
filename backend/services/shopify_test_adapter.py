"""Shopify checkout adapter configuration gate.

Deliberately does NOT create carts, orders, checkout URLs or process payments.
A future test-store adapter requires verified variant mapping and merchant credentials.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse


def shopify_test_readiness() -> dict:
    domain = os.getenv("LUMIERE_SHOPIFY_TEST_STORE_DOMAIN", "").strip().lower()
    enabled = os.getenv("LUMIERE_SHOPIFY_TEST_MODE", "0") == "1"
    valid_domain = bool(domain) and domain.endswith(".myshopify.com") and (
        urlparse("https://" + domain).hostname == domain
    ) and "/" not in domain
    return {
        "mode": "test_only",
        "configured": bool(enabled and valid_domain),
        "store_domain_configured": valid_domain,
        "checkout_enabled": False,
        "payment_enabled": False,
        "order_submission_enabled": False,
        "provider": "shopify",
        "missing_requirements": [
            "Authorised Shopify development store and sandbox credentials",
            "Verified Shopify variant IDs for each supplier SKU",
            "Test payment method, shipping and tax configuration",
            "Signed checkout return and order-status verification",
        ],
    }


def country_checkout_readiness(country: str) -> dict:
    """Non-operational launch checklist for approved test-store markets."""
    if country not in {"AU", "MD"}:
        raise ValueError("Unsupported delivery country")
    return {
        "country": country,
        "delivery_market": "Australia" if country == "AU" else "Moldova",
        "required_checks": [
            "Authorised Shopify development-store ownership and credentials",
            "Supplier SKU to Shopify variant mapping verified for each bag line",
            "Live supplier stock and final retail price confirmation",
            f"Verified shipping zones, rates, duties and tax rules for {country}",
            "Test payments, refunds, returns and order webhook signature verification",
        ],
        "checkout_enabled": False,
        "payment_enabled": False,
        "orders_enabled": False,
    }


def create_checkout(*args, **kwargs):
    raise RuntimeError(
        "Shopify cart and checkout are deliberately disabled until a verified "
        "development store and supplier variant mappings are available"
    )
