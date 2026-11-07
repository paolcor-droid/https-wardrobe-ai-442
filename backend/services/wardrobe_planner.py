"""Deterministic, explainable wardrobe outfit and capsule planning.

No live weather, inventory, purchase or fit claims. Suggestions use the user's
saved wardrobe labels; they do not infer garment colours from photographs.
"""
from __future__ import annotations

from collections import Counter


def _items(items):
    return [dict(item) for item in items if item.get("id") and item.get("name") and not item.get("deleted_at")]


def plan_outfits(items, occasion="casual", climate="mild", limit=12, *,
                 scan=None, preferred_colours=None, avoided_colours=None, preferred_style=None):
    """Rank owned combinations by labelled colour, style and saved-scan evidence.

    Use a bounded candidate pool; do not read garment pixels or infer fabric/fit.
    Preserve variety of owned shoes when there is just one base outfit.
    """
    from services.wardrobe_compatibility import score_owned_outfit
    if not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    items = _items(items)
    tops = [x for x in items if x.get("category") == "top"]
    bottoms = [x for x in items if x.get("category") == "bottom"]
    dresses = [x for x in items if x.get("category") == "dress"]
    shoes = [x for x in items if x.get("category") == "shoes"]
    outer = [x for x in items if x.get("category") == "outerwear"]
    # Bound work and avoid a 200-item wardrobe producing millions of sets.
    bases = ([[top, bottom] for top in tops for bottom in bottoms] +
             [[dress] for dress in dresses])[:1200]
    outfits = []
    seen = set()
    for index, base in enumerate(bases):
        shoe_options = shoes[:min(4, len(shoes))] if shoes else [None]
        # When there are many base outfits, rotate the first shoe so all
        # tied combinations do not just use the same accessory.
        if len(bases) > 1 and shoes:
            rotated = index % len(shoe_options)
            shoe_options = shoe_options[rotated:] + shoe_options[:rotated]
        for shoe in shoe_options:
            chosen = list(base)
            if shoe:
                chosen.append(shoe)
            if climate == "cold" and outer:
                chosen.append(outer[index % len(outer)])
            ids = tuple(x["id"] for x in chosen)
            if ids in seen:
                continue
            seen.add(ids)
            names = [x["name"] for x in chosen]
            evidence = score_owned_outfit(
                chosen, scan=scan, preferred_colours=preferred_colours,
                avoided_colours=avoided_colours, preferred_style=preferred_style,
                occasion=occasion, climate=climate)
            outfits.append({
                "item_ids": list(ids), "names": names,
                "reason": " ".join(evidence["compatibility_reasons"]),
                **evidence,
            })
    # Diversify the ranked set so one high-scoring shirt cannot consume all slots.
    # Always keep the highest-ranked look; use a small repetition penalty afterwards.
    ranked = sorted(outfits, key=lambda row: -row["compatibility_score"])
    selected = []
    used = Counter()
    while ranked and len(selected) < limit:
        index = max(range(len(ranked)), key=lambda i: (
            ranked[i]["compatibility_score"] -
            sum(9 * used[item_id] for item_id in ranked[i]["item_ids"]),
            -i))
        choice = ranked.pop(index)
        selected.append(choice)
        used.update(choice["item_ids"])
    return selected

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


def capsule_plan(items, occasion="casual", climate="mild", max_items=12, *,
                 scan=None, preferred_colours=None, avoided_colours=None, preferred_style=None):
    if not isinstance(max_items, int) or not 1 <= max_items <= 50:
        raise ValueError("max_items must be between 1 and 50")
    items = _items(items)
    priority = {"top": 0, "bottom": 1, "dress": 2, "shoes": 3, "outerwear": 4, "accessory": 5, "other": 6}
    # Select useful owned garments rather than alphabetical names. Full-outfit
    # compatibility is ranked using the same confirmed labels, scan and style
    # preferences as Discover, then balanced across garment categories.
    ranked_looks = plan_outfits(
        items, occasion, climate, limit=20, scan=scan,
        preferred_colours=preferred_colours,
        avoided_colours=avoided_colours,
        preferred_style=preferred_style)
    usefulness = Counter()
    for rank, look in enumerate(ranked_looks):
        for garment_id in look["item_ids"]:
            usefulness[garment_id] += max(1, 20 - rank)
    groups = {}
    for item in sorted(items, key=lambda x: (
            -usefulness[x["id"]], str(x.get("name") or "").casefold(), str(x["id"]))):
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
        "possible_outfits": plan_outfits(chosen, occasion, climate, limit=20, scan=scan,
                                        preferred_colours=preferred_colours,
                                        avoided_colours=avoided_colours,
                                        preferred_style=preferred_style),
        "missing_categories": missing,
        "wardrobe_insights": wardrobe_insights(items),
        "notice": "Capsule selection favours pieces used in your highest-ranked compatible owned outfits, then balances garment types. Rankings use confirmed garment details, not verified fit, stock or fabric.",
    }
