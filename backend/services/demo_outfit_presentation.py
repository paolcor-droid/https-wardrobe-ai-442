"""Readable, source-grounded copy and non-repetitive selections for demo looks."""
from collections import Counter
from services.demo_outfit_combinations import garment_role


def style_copy(garments, colours, occasion):
    pairs = list(zip(garments, colours))
    if not pairs:
        return {"title": "Coordinated outfit", "explanation": "Selected from eligible demo garments."}
    shoe = next(((p, c) for p, c in pairs if garment_role(p) == "shoes"), None)
    main = [c for p, c in pairs if garment_role(p) != "shoes"]
    base = Counter(main).most_common(1)[0][0] if main else colours[0]
    accent = shoe[1] if shoe else colours[-1]
    shoe_name = str(shoe[0].get("name") or "").casefold() if shoe else ""
    if "penny" in shoe_name and "loafer" in shoe_name:
        shoe_type = "Penny Loafers"
    elif "loafer" in shoe_name:
        shoe_type = "Loafers"
    elif "sneaker" in shoe_name:
        shoe_type = "Sneakers"
    elif "boot" in shoe_name:
        shoe_type = "Boots"
    elif "sandal" in shoe_name:
        shoe_type = "Sandals"
    else:
        shoe_type = "Footwear"
    if accent.casefold() != base.casefold():
        title = f"{base} with {accent} {shoe_type}" if shoe else f"{base} with {accent} accents"
        explanation = f"{base} anchors the outfit, with {accent} providing a contrasting footwear accent." if shoe else f"{base} anchors the outfit with a {accent} accent."
    else:
        title = f"{base} coordinated look"
        explanation = f"The selected pieces use a consistent {base} colour direction."
    if occasion:
        title = f"{occasion}: {title}"
    return {"title": title, "explanation": explanation}


def diversify_outfits(outfits, limit=16):
    """Select source-backed looks with a cap on repeated title/palette combinations.

    Never create new garments or silently alter personalisation eligibility.
    When there are fewer diverse looks than requested, return fewer cards.
    """
    remaining = sorted(outfits, key=lambda o: (-o["score"], o["id"]))
    selected = []
    title_counts = Counter()
    palette_counts = Counter()
    while remaining and len(selected) < limit:
        def title_key(o):
            return str(o.get("title") or "").casefold()
        def palette_key(o):
            return tuple(sorted(c.casefold() for g in o["garments"] for c in g.get("colour_names", [])))
        pool = [o for o in remaining if title_counts[title_key(o)] < 1 and palette_counts[palette_key(o)] < 2]
        if not pool:
            break
        winner = max(pool, key=lambda o: (o["score"], o["id"]))
        remaining.remove(winner)
        selected.append(winner)
        title_counts[title_key(winner)] += 1
        palette_counts[palette_key(winner)] += 1
    return selected
