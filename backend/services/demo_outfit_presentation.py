"""Readable, source-grounded copy and non-repetitive selections for demo looks."""
from collections import Counter
from services.demo_outfit_combinations import garment_role


def style_copy(garments, colours, occasion):
    """Ground titles in each selected garment and its actual selected colour."""
    pairs = list(zip(garments, colours))
    if not pairs:
        return {"title": "Coordinated outfit", "explanation": "Selected from eligible demo garments."}
    def label(garment, colour):
        name = str(garment.get("name") or "garment").strip()
        # Keep source names recognizable and never manufacture a garment subtype.
        return f"{colour} {name}".strip()
    labelled = [label(item, colour) for item, colour in pairs]
    if len(labelled) == 1:
        look = labelled[0]
    elif len(labelled) == 2:
        look = " and ".join(labelled)
    else:
        look = ", ".join(labelled[:-1]) + " and " + labelled[-1]
    title = f"{occasion}: {look}" if occasion else look
    unique = {str(c).casefold() for c in colours}
    explanation = ("The selected pieces use a consistent colour direction; individual fabrics and shades remain unverified."
                   if len(unique) == 1 else
                   "The selected garments combine " + ", ".join(dict.fromkeys(str(c) for c in colours)) +
                   "; colour swatches are illustrative, not verified fabric matches.")
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
    main_pair_counts = Counter()
    dominant_counts = Counter()
    while remaining and len(selected) < limit:
        eligible = []
        for o in remaining:
            signature = _look_signature(o)
            title = str(o.get("title") or "").casefold()
            if signature in seen_signatures or (title and title in seen_titles):
                continue
            if palette_counts[signature[1]] >= 2:
                continue
            main = tuple(sorted(set(g.get("colour_names", [""])[0].casefold() for g in o["garments"] if garment_role(g) != "shoes")))
            footwear = tuple(sorted(set(g.get("colour_names", [""])[0].casefold() for g in o["garments"] if garment_role(g) == "shoes")))
            if main_pair_counts[(main, footwear)] >= 2:
                continue
            eligible.append(o)
        if not eligible:
            break
        winner = max(eligible, key=lambda o: (
            o["score"]
            - 18 * palette_counts[_look_signature(o)[1]]
            - 8 * dominant_counts[next((g.get("colour_names", [""])[0].casefold()
                                      for g in o["garments"] if garment_role(g) != "shoes"), "")],
            o["id"]))
        remaining.remove(winner)
        selected.append(winner)
        sig = _look_signature(winner)
        seen_signatures.add(sig)
        seen_titles.add(str(winner.get("title") or "").casefold())
        palette_counts[sig[1]] += 1
        main = tuple(sorted(set(g.get("colour_names", [""])[0].casefold() for g in winner["garments"] if garment_role(g) != "shoes")))
        footwear = tuple(sorted(set(g.get("colour_names", [""])[0].casefold() for g in winner["garments"] if garment_role(g) == "shoes")))
        main_pair_counts[(main, footwear)] += 1
        if main:
            dominant_counts[next((g.get("colour_names", [""])[0].casefold() for g in winner["garments"] if garment_role(g) != "shoes"), "")] += 1
    return selected
