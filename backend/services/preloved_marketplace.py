"""Privacy-first Pre-Loved listing and personalised discovery helpers.

The personal stylist remains primary. Marketplace records expose no private images,
user identifiers, contact details, or scan data to other users. No payments,
seller-to-buyer messaging, or push notifications are implemented.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import re

from services.wardrobe_compatibility import colour_match, norm, score_owned_outfit

CONDITIONS = frozenset({"new with tags", "like new", "good", "fair"})
STATES = frozenset({"draft", "published", "paused", "withdrawn"})
MAX_PRICE = 10000.0


def validate_listing(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Invalid listing details")
    size = data.get("size", "")
    condition = data.get("condition", "")
    price = data.get("price")
    currency = data.get("currency", "AUD")
    description = data.get("description", "")
    delivery = data.get("delivery", "arrange later")
    if not isinstance(size, str) or not 1 <= len(size.strip()) <= 30:
        raise ValueError("Enter a garment size")
    if condition not in CONDITIONS:
        raise ValueError("Select a garment condition")
    if type(price) not in (int, float) or not math.isfinite(price) or not 1 <= price <= MAX_PRICE:
        raise ValueError("Invalid asking price")
    if currency != "AUD":
        raise ValueError("Pre-Loved pilot supports AUD listings only")
    if not isinstance(description, str) or len(description) > 500:
        raise ValueError("Description is too long")
    # No direct contact exchange until moderated messaging and safety controls exist.
    if re.search(r"(?:https?://|www\\.|@|\\b(?:\\+?\\d[ -]?){8,}\\d\\b)", description, re.I):
        raise ValueError("Do not include contact details or external links")
    if delivery != "arrange later":
        raise ValueError("Shipping and collection are not yet available")
    return {"size": size.strip(), "condition": condition, "price": round(price, 2),
            "currency": "AUD", "description": description.strip(), "delivery": delivery}


def public_listing(record: dict, garment: dict) -> dict:
    """Allowlisted anonymised fields only. Never include photo paths or seller IDs."""
    return {
        "id": record["id"], "name": str(garment.get("name") or "")[:120],
        "category": str(garment.get("category") or "")[:40],
        "colour": str(garment.get("colour") or "")[:80],
        "style": str(garment.get("style") or "")[:80],
        "pattern": str(garment.get("pattern") or "")[:80],
        "size": record["size"], "condition": record["condition"],
        "price": record["price"], "currency": record["currency"],
        "description": record.get("description", ""),
        "photo_available": False,  # Needs separate reviewed/public-media consent.
        "checkout_enabled": False, "messaging_enabled": False,
    }


def match_listing(listing: dict, *, profile: dict | None, wardrobe: list[dict]) -> dict:
    """Score only recipient data on the server, never reveal their private profile."""
    prefs = (profile or {}).get("preferences") or {}
    if listing.get("colour") and any(
        colour_match(listing["colour"], v)
        for v in prefs.get("avoided_colours", []) if isinstance(v, str)
    ):
        return {"eligible": False, "score": 0, "reason": "Explicitly avoided colour"}
    sizes = (profile or {}).get("sizes") or {}
    if not isinstance(sizes, dict):
        sizes = {}
    expected_size = sizes.get(listing.get("category")) or sizes.get("clothing")
    if expected_size and norm(expected_size) != norm(listing.get("size")):
        return {"eligible": False, "score": 0, "reason": "Size does not match"}
    owned = [item for item in wardrobe if not item.get("deleted_at")]
    colour_name = listing.get("colour", "")
    candidate = {"name": listing["name"], "category": listing["category"],
                 "colour": colour_name, "style": listing.get("style", "")}
    # Compare with existing pieces instead of ranking a product in isolation.
    complementary = [item for item in owned
                     if (candidate["category"] == "top" and item.get("category") == "bottom")
                     or (candidate["category"] == "bottom" and item.get("category") == "top")
                     or (candidate["category"] == "shoes" and item.get("category") in {"top", "bottom", "dress"})]
    context = complementary[:2]
    evidence = score_owned_outfit(
        context + [candidate], scan=(profile or {}).get("skin"),
        preferred_colours=prefs.get("preferred_colours"),
        avoided_colours=prefs.get("avoided_colours"),
        preferred_style=prefs.get("style"),
        occasion=prefs.get("occasion", "casual"),
        climate=prefs.get("climate", "mild"),
    )
    score = evidence["compatibility_score"]
    if context:
        score = min(100, score + 5)
    return {"eligible": True, "score": score,
            "reason": ("May complement garments in your wardrobe. " if context else "") +
                      " ".join(evidence["compatibility_reasons"][:3])}


def rank_pre_loved(listings: list[dict], profile: dict, wardrobe: list[dict], *,
                   min_score: int = 55, limit: int = 20) -> list[dict]:
    """Pure recipient-side ranking; seller and buyer identities remain hidden."""
    if not isinstance(min_score, int) or not 0 <= min_score <= 100:
        raise ValueError("Invalid threshold")
    results = []
    for listing in listings[:200]:
        evidence = match_listing(listing, profile=profile, wardrobe=wardrobe)
        if not evidence["eligible"] or evidence["score"] < min_score:
            continue
        results.append({**listing, "match_score": evidence["score"],
                        "match_reason": evidence["reason"]})
    results.sort(key=lambda x: (-x["match_score"], x["id"]))
    return results[:limit]
