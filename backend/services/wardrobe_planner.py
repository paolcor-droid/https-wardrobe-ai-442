"""Deterministic, explainable wardrobe outfit and capsule planning.

No live weather, inventory, purchase or fit claims. Suggestions use the user's
saved wardrobe labels; they do not infer garment colours from photographs.
"""
from __future__ import annotations

from collections import Counter


def _items(items):
    return [dict(item) for item in items if item.get("id") and item.get("name") and not item.get("deleted_at")]


def plan_outfits(items, occasion="casual", climate="mild", limit=12):
    items = _items(items)
    tops = [x for x in items if x.get("category") == "top"]
    bottoms = [x for x in items if x.get("category") == "bottom"]
    dresses = [x for x in items if x.get("category") == "dress"]
    shoes = [x for x in items if x.get("category") == "shoes"]
    outer = [x for x in items if x.get("category") == "outerwear"]
    outfits = []
    for top in tops:
        for bottom in bottoms:
            chosen = [top, bottom]
            if shoes:
                chosen.append(shoes[0])
            if climate == "cold" and outer:
                chosen.append(outer[0])
            outfits.append({
                "item_ids": [x["id"] for x in chosen],
                "names": [x["name"] for x in chosen],
                "reason": f"Your {top['name']} with {bottom['name']} for a {occasion} occasion; {climate} climate is a planning preference, not a live forecast.",
                "image_colour_verified": False,
            })
            if len(outfits) >= limit:
                return outfits
    for dress in dresses:
        chosen = [dress] + shoes[:1] + (outer[:1] if climate == "cold" else [])
        outfits.append({
            "item_ids": [x["id"] for x in chosen],
            "names": [x["name"] for x in chosen],
            "reason": f"Your {dress['name']} is an option for a {occasion} occasion. Check weather and fit before wearing.",
            "image_colour_verified": False,
        })
        if len(outfits) >= limit:
            break
    return outfits


def capsule_plan(items, occasion="casual", climate="mild", max_items=12):
    items = _items(items)
    priority = {"top": 0, "bottom": 1, "dress": 2, "shoes": 3, "outerwear": 4, "accessory": 5, "other": 6}
    chosen = sorted(items, key=lambda x: (priority.get(x.get("category"), 6), x.get("name", "")))[:max_items]
    counts = Counter(x.get("category") for x in chosen)
    missing = []
    if not counts["top"] and not counts["dress"]:
        missing.append("a versatile top or dress")
    if counts["top"] and not counts["bottom"]:
        missing.append("a versatile bottom")
    if not counts["shoes"]:
        missing.append("shoes suited to your occasion")
    if climate == "cold" and not counts["outerwear"]:
        missing.append("a layer for colder weather")
    return {
        "items": [{"id": x["id"], "name": x["name"], "category": x.get("category"), "colour": x.get("colour", "")} for x in chosen],
        "possible_outfits": plan_outfits(chosen, occasion, climate, limit=20),
        "missing_categories": missing,
        "notice": "Planning suggestions based on manually entered wardrobe labels, not live weather, visual garment verification or stock.",
    }
