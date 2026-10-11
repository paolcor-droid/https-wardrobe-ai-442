"""Deterministic, explainable wardrobe outfit and capsule planning.

No live weather, inventory, purchase or fit claims. Suggestions use the user's
saved wardrobe labels; they do not infer garment colours from photographs.
"""
from __future__ import annotations

from collections import Counter


def _items(items):
    return [dict(item) for item in items if item.get("id") and item.get("name") and not item.get("deleted_at")]


def plan_outfits(items, occasion="casual", climate="mild", limit=12):
    """Offer diverse combinations without claiming visual fit or weather verification."""
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    items = _items(items)
    tops = [x for x in items if x.get("category") == "top"]
    bottoms = [x for x in items if x.get("category") == "bottom"]
    dresses = [x for x in items if x.get("category") == "dress"]
    shoes = [x for x in items if x.get("category") == "shoes"]
    outer = [x for x in items if x.get("category") == "outerwear"]
    outfits = []
    seen = set()
    candidates = ([top, bottom] for top in tops for bottom in bottoms)
    candidates = list(candidates) + [[dress] for dress in dresses]
    # With just one base outfit, suggest alternative owned shoes rather than
    # silently discarding them. Bound the expansion by the requested limit.
    if len(candidates) == 1 and len(shoes) > 1:
        candidates = candidates * min(len(shoes), limit)
    for index, base in enumerate(candidates):
        chosen = list(base)
        if shoes:
            chosen.append(shoes[index % len(shoes)])
        if climate == "cold" and outer:
            chosen.append(outer[index % len(outer)])
        ids = tuple(x["id"] for x in chosen)
        if ids in seen:
            continue
        seen.add(ids)
        names = [x["name"] for x in chosen]
        outfits.append({
            "item_ids": list(ids),
            "names": names,
            "reason": (
                f"Try {' with '.join(names[:2])} for a {occasion} occasion. "
                f"The {climate} setting is your preference, not a live forecast. "
                "Check colour coordination, weather and fit yourself."
            ),
            "image_colour_verified": False,
        })
        if len(outfits) >= limit:
            break
    return outfits


def wardrobe_insights(items):
    """Explain potential wardrobe duplication using user-entered labels only.

    Never infer garment similarity, condition or fit from photographs.
    """
    items = _items(items)
    groups = {}
    for item in items:
        category = str(item.get("category") or "other").strip().casefold()
        colour = str(item.get("colour") or "").strip().casefold()
        name = " ".join(str(item.get("name") or "").strip().casefold().split())
        # Colour alone is insufficient evidence that two garments are duplicates.
        key = (category, colour, name)
        groups.setdefault(key, []).append(item)
    duplicates = []
    for (category, colour, name), members in groups.items():
        if len(members) > 1:
            duplicates.append({
                "category": category, "colour": colour, "name": name,
                "item_ids": [member["id"] for member in members],
                "reason": "These items share the same manually entered name, category and colour; confirm whether they are actually duplicates.",
            })
    return {
        "possible_duplicates": duplicates,
        "item_count": len(items),
        "notice": "Possible duplicates are based on manually entered labels, not image comparison.",
    }


def capsule_plan(items, occasion="casual", climate="mild", max_items=12):
    if not isinstance(max_items, int) or not 1 <= max_items <= 50:
        raise ValueError("max_items must be between 1 and 50")
    items = _items(items)
    priority = {"top": 0, "bottom": 1, "dress": 2, "shoes": 3, "outerwear": 4, "accessory": 5, "other": 6}
    groups = {}
    for item in sorted(items, key=lambda x: (str(x.get("name") or "").casefold(), str(x["id"]))):
        groups.setdefault(item.get("category") or "other", []).append(item)
    # Take one from each relevant category first. The previous alphabetical
    # truncation could fill the entire capsule with tops, yielding no outfits.
    order = ["top", "bottom", "dress", "shoes"]
    if climate == "cold":
        order.append("outerwear")
    order += ["accessory", "other"]
    if climate != "cold":
        order.append("outerwear")
    chosen = []
    for category in order:
        if groups.get(category) and len(chosen) < max_items:
            chosen.append(groups[category].pop(0))
    remaining = sorted(
        [item for group in groups.values() for item in group],
        key=lambda x: (priority.get(x.get("category"), 6), str(x.get("name") or "").casefold()),
    )
    chosen.extend(remaining[:max(0, max_items - len(chosen))])
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
        "wardrobe_insights": wardrobe_insights(items),
        "notice": "Planning suggestions based on manually entered wardrobe labels, not live weather, visual garment verification or stock.",
    }
