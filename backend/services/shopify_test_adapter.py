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


def create_checkout(*args, **kwargs):
    raise RuntimeError(
        "Shopify cart and checkout are deliberately disabled until a verified "
        "development store and supplier variant mappings are available"
    )
