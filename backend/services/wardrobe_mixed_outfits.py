"""Rank owned-first outfits; suggest catalogue products only for missing garment roles.

Catalogue records are snapshots, NOT verified live stock or prices. Never create
orders, prepare private image files, or call paid image generation here.
"""
from services.wardrobe_planner import plan_outfits
from services.wardrobe_compatibility import score_owned_outfit, norm

ROLES = ("top", "bottom", "dress", "shoes")


def mixed_outfits(owned, products, *, scan=None, preferences=None, limit=8):
    prefs = preferences or {}
    owned = [dict(g) for g in owned if g.get("id") and not g.get("deleted_at")]
    complete = plan_outfits(
        owned, limit=limit, scan=scan,
        preferred_colours=prefs.get("preferred_colours"),
        avoided_colours=prefs.get("avoided_colours"),
        preferred_style=prefs.get("style"),
        occasion=prefs.get("occasion", "casual"),
        climate=prefs.get("climate", "mild"))
    results = []
    for look in complete:
        results.append({
            "id": "owned:" + "|".join(look["item_ids"]),
            "owned_ids": look["item_ids"], "suggested_products": [],
            "score": look["compatibility_score"], "reason": look["reason"],
            "type": "all_owned", "purchase_required": False,
        })
    # Fill an actual gap only; do not replace available owned pieces to sell more.
    tops = [g for g in owned if g.get("category") == "top"]
    bottoms = [g for g in owned if g.get("category") == "bottom"]
    dresses = [g for g in owned if g.get("category") == "dress"]
    if tops and not bottoms:
        missing, anchors = "bottom", tops
    elif bottoms and not tops and not dresses:
        missing, anchors = "top", bottoms
    elif (tops and bottoms or dresses) and not any(g.get("category") == "shoes" for g in owned):
        missing, anchors = "shoes", (tops[:3] + bottoms[:3]) if tops and bottoms else dresses[:3]
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
                "type": "wardrobe_plus_catalogue", "purchase_required": True,
            })
    # Keep owned-first suggestions at the front; do not promote shopping unnecessarily.
    return {"outfits": results[:limit], "notice": (
        "Owned garments are prioritised. Catalogue suggestions are snapshot-based; "
        "availability, price and colour are unverified. No orders or payments."
    )}
