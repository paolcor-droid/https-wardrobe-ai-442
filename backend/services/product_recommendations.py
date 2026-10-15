"""Provider-neutral ranking pipeline for verified catalogue products.

This module never retrieves, fabricates, or labels products as live. It only
ranks already-normalized, source-backed records supplied by catalogue providers.
"""
from __future__ import annotations

from typing import Iterable

from services.customer_pricing import PricingPolicy, apply_customer_price
from services.recommendation_engine import is_colour_eligible, recommendation_reasons, recommendation_score, scan_colour_evidence, _product_colour_names, _colour_match, _norm_colour

# LUMIÈRE retails wholesale-sourced trial products at a fixed +25% markup.
# Supplier cost stays private; the customer only ever sees this derived price.
LUMIERE_WHOLESALE_POLICY = PricingPolicy(markup_percent=25)



def _is_sleepwear(product: dict) -> bool:
    label = " ".join(str(product.get(key) or "") for key in ("name", "category", "category_path")).lower()
    return any(word in label for word in ("pyjama", "pajama", "sleepwear", "nightwear", "nightdress", "underwear", "boxer", "briefs", "lingerie", "panties", "knickers", "bra "))


def _wants_sleepwear(prefs: dict) -> bool:
    selection = (" ".join(str(x) for x in (prefs.get("categories") or [])) + " " + str(prefs.get("occasion") or "")).lower()
    return any(word in selection for word in ("sleep", "nightwear", "pyjama", "pajama", "underwear", "lingerie"))



def _everyday_priority(product: dict) -> float:
    """Small ranking boost for versatile daily clothing, without bypassing filters."""
    label = " ".join(str(product.get(key) or "") for key in ("name", "category", "category_path")).lower()
    primary = ("shirt", "polo", "trouser", "chino", "jean", "short", "blouse", "t-shirt", "tee ")
    secondary = ("dress", "skirt", "top", "jumper", "sweater", "cardigan", "jacket", "blazer")
    if any(term in label for term in primary):
        return 12.0
    if any(term in label for term in secondary):
        return 5.0
    return 0.0


def _diversify_brands(ranked: list[dict], limit: int) -> list[dict]:
    """Balance brand and clothing type without fabricating variety."""
    remaining = ranked[:5000]
    selected = []
    brand_counts = {}
    type_counts = {}
    def kind(item):
        label = " ".join(str(item.get(k) or "") for k in ("name", "category", "category_path")).lower()
        for group, words in (
            ("swimwear", ("swimming", "swimwear", "swim trunks", "bikini")),
            ("underwear", ("underwear", "boxer", "briefs", "singlet")),
            ("sleepwear", ("pyjama", "pajama", "sleepwear")),
            ("shirts", ("shirt", "polo", "blouse", "tee ")),
            ("trousers", ("trouser", "chino", "jean", "pants")),
            ("shorts", ("short",)),
            ("dresses", ("dress", "skirt")),
        ):
            if any(word in label for word in words):
                return group
        return "other"
    while remaining and len(selected) < limit:
        def adjusted(item):
            brand = str(item.get("brand") or "Unknown").casefold()
            return item["recommendation_score"] - 4 * min(brand_counts.get(brand, 0), 3) - 6 * min(type_counts.get(kind(item), 0), 4)
        winner = max(remaining, key=adjusted)
        remaining.remove(winner)
        selected.append(winner)
        brand = str(winner.get("brand") or "Unknown").casefold()
        category = kind(winner)
        brand_counts[brand] = brand_counts.get(brand, 0) + 1
        type_counts[category] = type_counts.get(category, 0) + 1
    return selected


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
    shop_for = prefs.get("shop_for") or "all"
    allow_sleepwear = _wants_sleepwear(prefs)

    for product in products:
        if not product.get("live"):
            continue
        if not product.get("source_verified"):
            continue
        if not product.get("external_id") or not product.get("name"):
            continue

        # Strict colour eligibility: scan palette or preferred colours,
        # with avoided colours always excluded.
        if not is_colour_eligible(
            product,
            colour_profile,
            prefs.get("preferred_colours"),
            prefs.get("avoided_colours"),
        ):
            continue

        # Department is a HARD filter applied before scoring: a Men preference
        # can never surface Women products (and vice versa). Genuine unisex items
        # are allowed for either. "all" imposes no department restriction.
        if shop_for in ("mens", "womens") and product.get("department") not in (shop_for, "unisex"):
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

        # Derive the LUMIÈRE customer price from wholesale supplier cost (+25%)
        # so supplier cost is never surfaced and budget filters use a real price.
        if product.get("provider_kind") == "wholesale" and product.get("customer_price") is None:
            product = apply_customer_price(product, LUMIERE_WHOLESALE_POLICY)

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

        label = " ".join(str(product.get(k) or "") for k in ("name", "category", "category_path")).lower()
        swim_requested = any(term in (" ".join(str(x) for x in (prefs.get("categories") or [])) + " " + str(prefs.get("occasion") or "")).lower() for term in ("swim", "beach", "pool"))
        swimwear = any(term in label for term in ("swimming", "swimwear", "swim trunks", "bikini", "beachwear"))
        underwear = any(term in label for term in ("underwear", "boxer", "briefs", "lingerie", "panties", "knickers", "singlet"))
        if (swimwear and not swim_requested) or ((underwear or _is_sleepwear(product)) and not allow_sleepwear):
            score -= 22  # Soft penalty: limited catalogues can still show these later.
        else:
            score += _everyday_priority(product)

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

        evidence = scan_colour_evidence(product, colour_profile)
        palette_matches = sorted(set().union(
            evidence["best_neutrals"], evidence["best_accents"], evidence["statement_colours"]
        ))
        preferred_matches = sorted(_colour_match(
            _product_colour_names(product),
            {_norm_colour(str(c)) for c in (prefs.get("preferred_colours") or []) if c},
        ))
        colour_match = {
            "basis": "both" if palette_matches and preferred_matches else
                     "skin_palette" if palette_matches else
                     "preferred_colour" if preferred_matches else "unverified",
            "skin_palette_colours": palette_matches,
            "preferred_colours": preferred_matches,
            "evidence_source": "supplier_colour_label",
            "image_colour_verified": False,
        }

        ranked.append({
            "colour_match": colour_match,
            **product,
            "recommendation_score": round(score, 1),
            "recommendation_reasons": reasons,
        })

    ranked.sort(key=lambda item: item["recommendation_score"], reverse=True)
    return _diversify_brands(ranked, max(0, limit))


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
        "colour_match": product.get("colour_match"),
    }


def customer_recommendations(products: Iterable[dict]) -> list[dict]:
    return [customer_product_view(product) for product in products]
