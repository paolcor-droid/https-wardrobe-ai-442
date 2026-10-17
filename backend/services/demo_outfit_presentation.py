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
        # A monochrome look still needs to say what the garments actually are.
        roles = [(garment_role(p), str(p.get("name") or "")) for p, _ in pairs]
        top_name = next((name for role, name in roles if role in ("top", "dress")), "")
        bottom_name = next((name for role, name in roles if role == "bottom"), "")
        if top_name and bottom_name:
            title = f"{base} {top_name} with {bottom_name}"
        elif top_name:
            title = f"{base} {top_name} outfit"
        else:
            title = f"{base} coordinated outfit"
        explanation = f"The selected pieces use a consistent {base} colour direction."
    if occasion:
        title = f"{occasion}: {title}"
    return {"title": title, "explanation": explanation}


def _look_signature(outfit):
    """Compare visual silhouettes and dominant colours, not SKU identities."""
    garments = outfit["garments"]
    roles = []
    for g in garments:
        name = str(g.get("name") or "").casefold()
        role = garment_role(g)
        if role == "top":
            subtype = ("sweatshirt" if any(t in name for t in ("sweatshirt", "hoodie", "sweater")) else
                       "t-shirt" if "t-shirt" in name or "tee" in name else
                       "shirt" if "shirt" in name else "top")
        elif role == "bottom":
            subtype = "shorts" if "short" in name else "skirt" if "skirt" in name else "trousers"
        elif role == "shoes":
            subtype = "loafers" if "loafer" in name else "sneakers" if "sneaker" in name else "boots" if "boot" in name else "shoes"
        else:
            subtype = role
        roles.append(subtype)
    palette = tuple(sorted(set(c.casefold() for g in garments for c in g.get("colour_names", []))))
    return tuple(sorted(roles)), palette


def diversify_outfits(outfits, limit=16):
    """Show a selective edit of visually different looks.

    A duplicate silhouette/palette cannot reappear, even if its underlying SKU,
    brand or price differs. Return fewer than the limit if diversity is low.
    """
    remaining = sorted(outfits, key=lambda o: (-o["score"], o["id"]))
    selected = []
    seen_signatures = set()
    seen_titles = set()
    palette_counts = Counter()
    while remaining and len(selected) < limit:
        eligible = []
        for o in remaining:
            signature = _look_signature(o)
            title = str(o.get("title") or "").casefold()
            if signature in seen_signatures or (title and title in seen_titles):
                continue
            if palette_counts[signature[1]] >= 2:
                continue
            eligible.append(o)
        if not eligible:
            break
        winner = max(eligible, key=lambda o: (o["score"] - 7 * palette_counts[_look_signature(o)[1]], o["id"]))
        remaining.remove(winner)
        selected.append(winner)
        sig = _look_signature(winner)
        seen_signatures.add(sig)
        seen_titles.add(str(winner.get("title") or "").casefold())
        palette_counts[sig[1]] += 1
    return selected
