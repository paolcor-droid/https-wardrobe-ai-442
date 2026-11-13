"""Coordinated outfits from real, pre-eligible supplier catalogue snapshots.

The caller must apply account colour, department, budget and product feedback
filters first. This module never creates stock, prices, images or products.
"""
from services.demo_outfit_combinations import garment_role, harmony

def eligible_outfit_roles(products):
    """Count source-backed women/unisex items with photos by styling role."""
    counts = {name: 0 for name in ("top", "bottom", "dress", "shoes")}
    for p in products:
        if p.get("department") in ("womens", "unisex") and p.get("source_verified") and p.get("image_url"):
            role = garment_role(p)
            if role in counts:
                counts[role] += 1
    return counts


def build_supplier_outfits(products, limit=8, diagnostics=None):
    """Build genuine eligible looks, including legitimate monochrome styling.

    Diagnostics describe why candidate outfits were rejected without exposing
    product records or personal profile data.
    """
    rejected = {"repeated_or_duplicate": 0, "missing_colour": 0,
                "harmony": 0, "accepted": 0}
    if diagnostics is not None:
        diagnostics.update(rejected)
    roles = {name: [] for name in ("top", "bottom", "dress", "shoes")}
    for product in products:
        if product.get("department") not in ("womens", "unisex"):
            continue
        if not product.get("source_verified") or not product.get("image_url"):
            continue
        role = garment_role(product)
        if role in roles and len(roles[role]) < 100:
            roles[role].append(product)
    results = []
    seen = set()
    def add(garments):
        ids = tuple(str(p.get("external_id")) for p in garments)
        if len(ids) != len(set(ids)) or ids in seen:
            rejected["repeated_or_duplicate"] += 1
            return
        seen.add(ids)
        colours = [(p.get("colour_names") or [""])[0] for p in garments]
        # Some genuine supplier records do not contain a colour label.
        # Such looks remain provisional; do not invent the missing shade.
        missing_colours = any(not str(c).strip() for c in colours)
        if missing_colours:
            rejected["missing_colour"] += 1
            labelled = [c for c in colours if str(c).strip()]
            if not labelled:
                points, reason = -6, "Supplier colour labels are missing; visual harmony is unverified."
            else:
                points, reason = -4, "Some supplier colour labels are missing; check the product photos."
        elif len({str(c).strip().casefold() for c in colours}) == 1:
            # The shared demo heuristic rejects identical names because
            # fabric shades cannot be proven. That is not a valid hard
            # exclusion for real monochromatic outfits (e.g. black+black).
            points, reason = 0, "Monochrome styling; check actual shades and textures in product photos."
        else:
            points, reason = harmony(colours)
            if points < -2:
                rejected["harmony"] += 1
                return
        # Explicitly reject incompatible saturated colour families; neutral bags
        # are considered independently by the frontend.
        score = sum(float(p.get("recommendation_score") or 0) for p in garments) / len(garments) + points
        customer_items = []
        for p, colour in zip(garments, colours):
            # No upstream wholesale price in the response.
            price = p.get("customer_price")
            customer_items.append({
                "product_id":str(p.get("external_id")),
                "name":p.get("name"), "brand":p.get("brand"),
                "category":p.get("category"), "colour_names":[colour],
                "image_url":p.get("image_url"), "price":price,
                "currency":p.get("currency"),
            })
        rejected["accepted"] += 1
        results.append({"id":"supplier-outfit:"+":".join(ids),
            "garments":customer_items, "score":round(score,1),
            "reason":reason+" Check real product photographs to confirm shades and proportions.",
            "price_verified_live":False,"stock_verified_live":False})
    # Limit combinatorial work, but rotate candidate offsets to avoid repeating
    # the same top/dress. Each product has passed the account's hard filters.
    for offset in range(96):
        if roles["top"] and roles["bottom"]:
            pair = [roles["top"][offset%len(roles["top"])],
                    roles["bottom"][(offset*7)%len(roles["bottom"])]]
            if roles["shoes"]:
                pair.append(roles["shoes"][(offset*11)%len(roles["shoes"])])
            add(pair)
        if roles["dress"]:
            look = [roles["dress"][offset%len(roles["dress"])]]
            if roles["shoes"]:
                look.append(roles["shoes"][(offset*7)%len(roles["shoes"])])
            add(look)
    results.sort(key=lambda x:(-x["score"],x["id"]))
    # Diversify by the actual first product so the rail isn't 8 nearly identical looks.
    output = []
    first_seen = set()
    for row in results:
        first = row["garments"][0]["product_id"]
        if first in first_seen:
            continue
        first_seen.add(first)
        output.append(row)
        if len(output)>=limit:
            break
    if diagnostics is not None:
        diagnostics.update(rejected)
    return output
