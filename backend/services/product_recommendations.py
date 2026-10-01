"""Provider-neutral ranking pipeline for verified catalogue products.

This module never retrieves, fabricates, or labels products as live. It only
ranks already-normalized, source-backed records supplied by catalogue providers.
"""
from __future__ import annotations

from typing import Iterable

from services.recommendation_engine import recommendation_reasons, recommendation_score


def rank_verified_products(
    products: Iterable[dict],
    profile: dict,
    limit: int = 20,
) -> list[dict]:
    """Rank verified catalogue records against the active LUMIÈRE profile.

    Products must already have been normalized by catalogue_providers.normalize_product.
    Records that fail hard filters (score < 0) are excluded.
    """
    prefs = profile.get("preferences") or {}
    colour_profile = profile.get("skin")
    ranked: list[dict] = []

    preferred_retailers = set(prefs.get("preferred_retailers") or [])
    categories = set(prefs.get("categories") or [])
    budget_min = prefs.get("budget_min")
    budget_max = prefs.get("budget_max")

    for product in products:
        if not product.get("live"):
            continue
        if not product.get("source_verified"):
            continue
        if not product.get("external_id") or not product.get("name"):
            continue

        # Wholesale feeds may contain genuine products that are currently out of
        # stock. Keep them out of recommendations until at least one unit exists.
        availability = product.get("availability")
        if availability is not None:
            try:
                if float(availability) <= 0:
                    continue
            except (TypeError, ValueError):
                pass

        # Budget filters must use the price the customer would actually pay.
        # Wholesale supplier cost is private and is not a valid budget signal.
        price = product.get("customer_price") if product.get("provider_kind") == "wholesale" else product.get("price")
        if budget_min is not None and price is not None and price < budget_min:
            continue

        if categories and product.get("category") and product["category"] not in categories:
            continue

        scoring_product = dict(product)
        scoring_product["price"] = price
        score = recommendation_score(
            scoring_product,
            colour_profile,
            prefs.get("occasion"),
            budget_max,
            prefs.get("climate"),
            prefs.get("style"),
            prefs.get("preferred_colours"),
            prefs.get("avoided_colours"),
        )
        if score < 0:
            continue

        # Preference, not a hard filter: verified products from other providers
        # can still surface when they are a substantially better wardrobe match.
        if preferred_retailers and product.get("provider_id") in preferred_retailers:
            score += 5

        reasons = recommendation_reasons(
            scoring_product,
            colour_profile,
            prefs.get("occasion"),
            prefs.get("climate"),
            prefs.get("style"),
            prefs.get("preferred_colours"),
            prefs.get("avoided_colours"),
        )

        ranked.append({
            **product,
            "recommendation_score": round(score, 1),
            "recommendation_reasons": reasons,
        })

    ranked.sort(key=lambda item: item["recommendation_score"], reverse=True)
    return ranked[: max(0, limit)]


def customer_product_view(product: dict) -> dict:
    """Return only fields safe for a LUMIÈRE-owned storefront.

    Upstream supplier identity, provider IDs, wholesale source URLs and internal
    availability metadata stay server-side. This projection is for products
    sold by LUMIÈRE, not referral/affiliate retailer links.
    """
    return {
        "product_id": product.get("external_id"),
        "name": product.get("name"),
        "brand": product.get("brand"),
        "category": product.get("category"),
        "description": product.get("description", ""),
        # Never fall back to supplier cost in a LUMIÈRE-owned storefront.
        "price": product.get("customer_price"),
        "currency": product.get("currency"),
        "image_url": product.get("image_url"),
        "colour_names": product.get("colour_names", []),
        "sizes": product.get("sizes", []),
        "materials": product.get("materials", []),
        "recommendation_score": product.get("recommendation_score"),
        "recommendation_reasons": product.get("recommendation_reasons", []),
    }


def customer_recommendations(products: Iterable[dict]) -> list[dict]:
    return [customer_product_view(product) for product in products]
