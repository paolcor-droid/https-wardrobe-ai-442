"""Rank owned-first outfits; suggest catalogue products only for missing garment roles.

Catalogue records are snapshots, NOT verified live stock or prices. Never create
orders, prepare private image files, or call paid image generation here.
"""
from services.wardrobe_planner import plan_outfits
from services.wardrobe_compatibility import score_owned_outfit, norm

ROLES = ("top", "bottom", "dress", "shoes")


def mixed_outfits(owned, products, *, scan=None, preferences=None, feedback=None, limit=8):
    prefs = preferences or {}
    owned = [dict(g) for g in owned if g.get("id") and not g.get("deleted_at")]
    if prefs.get("shop_for") in ("mens", "womens"):
        owned = [g for g in owned if g.get("shop_for") in (prefs["shop_for"], "all")]
    complete = plan_outfits(
        owned, limit=limit, scan=scan,
        preferred_colours=prefs.get("preferred_colours"),
        avoided_colours=prefs.get("avoided_colours"),
        preferred_style=prefs.get("style"),
        occasion=prefs.get("occasion", "casual"),
        climate=prefs.get("climate", "mild"), feedback=feedback,
        shop_for=prefs.get("shop_for"))
    results = []
    for look in complete:
        results.append({
            "id": "owned:" + "|".join(look["item_ids"]),
            "owned_ids": look["item_ids"], "suggested_products": [],
            "score": look["compatibility_score"], "reason": look["reason"],
            "is_complete": look["is_complete"],
            "missing_categories": look["missing_categories"],
            "type": "all_owned", "purchase_required": False,
        })
    # Preserve the planner's personalised ordering, which also handles ties
    # at the displayed 95-point ceiling. Never double-count feedback here.
    # Fill an actual gap only; do not replace available owned pieces to sell more.
    tops = [g for g in owned if g.get("category") == "top"]
    bottoms = [g for g in owned if g.get("category") == "bottom"]
    dresses = [g for g in owned if g.get("category") == "dress"]
    if tops and not bottoms:
        missing, anchors = "bottom", tops
    elif bottoms and not tops and not dresses:
        missing, anchors = "top", bottoms
    elif (tops and bottoms or dresses) and not any(g.get("category") == "shoes" for g in owned):
        missing = "shoes"
        # Anchor shopping suggestions to an actual top+bottom or dress outfit.
        # The previous list of tops followed by bottoms could select two tops.
        by_id = {g["id"]: g for g in owned}
        anchors = ([by_id[i] for i in complete[0]["item_ids"] if i in by_id]
                   if complete else ([tops[0], bottoms[0]] if tops and bottoms else dresses[:1]))
    else:
        missing, anchors = None, []
    if missing:
        eligible = []
        for product in products[:200]:
            if not isinstance(product, dict) or norm(product.get("category")) not in {
                missing, missing + "s", "footwear" if missing == "shoes" else missing
            }:
                continue
            pid = product.get("product_id")
            if not isinstance(pid, str) or not pid or not product.get("name"):
                continue
            colour = (product.get("colour_names") or [""])[0]
            g = {"id": pid, "name": product["name"], "category": missing,
                 "colour": colour, "style": ""}
            evidence = score_owned_outfit(
                anchors[:2] + [g], scan=scan,
                preferred_colours=prefs.get("preferred_colours"),
                avoided_colours=prefs.get("avoided_colours"),
                preferred_style=prefs.get("style"),
                occasion=prefs.get("occasion", "casual"),
                climate=prefs.get("climate", "mild"))
            eligible.append((evidence["compatibility_score"], pid, product, evidence))
        for score, pid, product, evidence in sorted(eligible, key=lambda x: -x[0])[:3]:
            results.append({
                "id": "mixed:" + pid, "owned_ids": [g["id"] for g in anchors[:2]],
                "suggested_products": [{
                    "product_id": pid, "name": product["name"],
                    "category": missing, "image_url": product.get("image_url"),
                    "price": product.get("price"), "currency": product.get("currency"),
                    "price_verified": False, "stock_verified": False,
                }],
                "score": score, "reason": " ".join(evidence["compatibility_reasons"]),
                "is_complete": False, "missing_categories": [missing],
                "type": "wardrobe_plus_catalogue", "purchase_required": True,
            })
    # Reserve a small number of slots for missing-piece options when available.
    # Otherwise 8 owned combinations can hide every suggestion for missing shoes.
    # Owned looks always appear first and remain the majority.
    owned_results = [row for row in results if not row["purchase_required"]]
    gap_results = [row for row in results if row["purchase_required"]]
    gap_count = min(len(gap_results), 2, max(0, limit - 1)) if owned_results else min(len(gap_results), limit)
    shown = owned_results[:limit - gap_count] + gap_results[:gap_count]
    return {"outfits": shown, "notice": (
        "Owned garments are prioritised. Up to two optional matching pieces fill actual gaps. "
        "Catalogue availability, price and colours are unverified. No orders or payments."
    )}
