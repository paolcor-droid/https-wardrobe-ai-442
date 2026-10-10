"""Matterhorn catalogue ingestion for LUMIÈRE development and sync jobs."""
from __future__ import annotations

from typing import Iterable

from services.catalogue_providers import normalize_product
from services.matterhorn_xml import PROVIDER_ID, iter_products
from services.product_recommendations import rank_verified_products, customer_recommendations


def normalized_products(xml_path: str, *, in_stock_only: bool = True, limit: int | None = None):
    """Stream genuine Matterhorn XML records into the provider-neutral contract."""
    emitted = 0
    for raw in iter_products(xml_path):
        if in_stock_only:
            try:
                if float(raw.get("availability") or 0) <= 0:
                    continue
            except (TypeError, ValueError):
                continue

        # normalize_product intentionally exposes only the common catalogue
        # contract. Matterhorn-specific variants remain private to ingestion.
        normalized = normalize_product(PROVIDER_ID, raw)
        yield normalized
        emitted += 1
        if limit is not None and emitted >= max(0, limit):
            return


def recommend_from_xml(
    xml_path: str,
    profile: dict,
    *,
    scan_limit: int = 5000,
    recommendation_limit: int = 20,
) -> list[dict]:
    """Rank a bounded set of real, in-stock Matterhorn products for LUMIÈRE.

    The bounded scan is a development bridge. Production should use a persisted
    normalized catalogue or authorised API sync rather than re-reading 71 MB on
    every customer request.
    """
    products = normalized_products(xml_path, in_stock_only=True, limit=scan_limit)
    ranked = rank_verified_products(products, profile, limit=recommendation_limit)
    return customer_recommendations(ranked)
