"""Conservative explainable ranking of *owned* garments using confirmed labels.

No image-colour inference, no live weather and no skin-type assumptions.
Scores compare garments within a user's own wardrobe; not probabilities.
"""
from __future__ import annotations

import math
from services.recommendation_engine import COLOUR_EQUIVALENTS

NEUTRALS = frozenset({
    "black", "white", "cream", "ivory", "beige", "sand", "tan", "taupe",
    "grey", "gray", "charcoal", "navy", "navy blue", "soft navy", "brown",
})


def norm(value):
    return " ".join(str(value or "").casefold().replace("_", " ").replace("-", " ").split())


def colour_match(a, b):
    a, b = norm(a), norm(b)
    return bool(a and b and (a == b or b in COLOUR_EQUIVALENTS.get(a, ()) or a in COLOUR_EQUIVALENTS.get(b, ())))


def palette_names(scan, key):
    return [x.get("name", "") for x in (scan or {}).get(key, []) if isinstance(x, dict) and x.get("name")]


def score_owned_outfit(garments, *, scan=None, preferred_colours=None, avoided_colours=None,
                       preferred_style=None, occasion="casual", climate="mild"):
    """Return deterministic relative score and evidence; no fabric/fit verification."""
    score = 50
    reasons = []
    preferred = [str(v) for v in (preferred_colours or []) if isinstance(v, str)]
    avoided = [str(v) for v in (avoided_colours or []) if isinstance(v, str)]
    neutrals = 0
    matched_palette = 0
    caution = 0
    labelled = 0
    styles = []
    for garment in garments:
        colour = norm(garment.get("colour"))
        style = norm(garment.get("style"))
        if style and style != "other":
            styles.append(style)
        if not colour:
            continue
        labelled += 1
        if colour in NEUTRALS:
            neutrals += 1
        if any(colour_match(colour, v) for v in avoided):
            score -= 32
            reasons.append(f"{garment['name']} has a colour you chose to avoid.")
        if any(colour_match(colour, v) for v in preferred):
            score += 12
            reasons.append(f"{garment['name']} matches a preferred clothing colour.")
        if any(colour_match(colour, v) for v in palette_names(scan, "best_neutrals")):
            score += 15
            matched_palette += 1
        elif any(colour_match(colour, v) for v in palette_names(scan, "best_accents")):
            score += 18
            matched_palette += 1
        elif any(colour_match(colour, v) for v in palette_names(scan, "statement_colours")):
            score += 8
            matched_palette += 1
        if any(colour_match(colour, v) for v in palette_names(scan, "caution_colours")):
            score -= 16
            caution += 1
    if matched_palette:
        reasons.append(f"{matched_palette} garment colour(s) match named swatches in your saved scan.")
    if caution:
        reasons.append(f"{caution} garment colour(s) match your scan's caution swatches.")
    colours = [norm(g.get("colour")) for g in garments if norm(g.get("colour"))]
    if len(colours) >= 2:
        if len(set(colours)) == 1:
            score += 10
            reasons.append("The saved colour labels suggest a tonal outfit.")
        elif neutrals:
            score += 8
            reasons.append("A labelled neutral provides a versatile colour base.")
        elif len(set(colours)) >= 3:
            score -= 5
            reasons.append("Several different labelled colours may need visual coordination.")
    # Whole-look harmony matters independently of individual skin-swatch matches.
    # Conservative named-colour families; do not infer colour from image pixels.
    families = {
        "navy": "blue", "navy blue": "blue", "soft navy": "blue",
        "light blue": "blue", "blue": "blue", "cobalt": "blue",
        "burgundy": "red", "red": "red", "rose": "pink", "soft rose": "pink",
        "pink": "pink", "forest green": "green", "green": "green",
        "olive": "green", "sage": "green", "orange": "orange",
        "rust": "orange", "yellow": "yellow", "purple": "purple",
        "lavender": "purple",
    }
    accent_families = {families.get(c, c) for c in colours if c not in NEUTRALS}
    if len(accent_families) == 1 and len(colours) >= 2:
        score += 8
        reasons.append("The labelled colours form a coordinated neutral-and-accent palette.")
    elif len(accent_families) >= 3:
        score -= 12
        reasons.append("The outfit combines several accent colour families; review harmony visually.")
    requested_style = norm(preferred_style)
    if requested_style and styles:
        matching = sum(style == requested_style for style in styles)
        score += 14 * matching
        if matching:
            reasons.append(f"{matching} garment(s) match your preferred {requested_style} style.")
    if len(styles) > 1 and len(set(styles)) == 1:
        score += 10
        reasons.append("The saved garment styles are consistent.")
    # Evaluate the look as a composition, not just a sum of matching skin
    # swatches. A neutral foundation and one accent generally coordinate more
    # easily than several independently strong accents. Unknown labels stay
    # neutral so we never infer patterns or fabrics from photographs.
    core = [g for g in garments if g.get("category") in {"top", "bottom", "dress"}]
    core_colours = [norm(g.get("colour")) for g in core if norm(g.get("colour"))]
    core_accents = [c for c in core_colours if c not in NEUTRALS]
    if len(core_colours) >= 2 and len(core_accents) == 1:
        score += 5
        reasons.append("A single labelled accent balances the core garments.")
    patterns = [norm(g.get("pattern")) for g in core]
    distinct_patterns = [p for p in patterns if p and p not in {"solid", "plain", "none", "other"}]
    if len(distinct_patterns) >= 2:
        score -= 12
        reasons.append("Both core garments have labelled patterns; check that their scales coordinate.")
    elif len(distinct_patterns) == 1:
        score += 3
        reasons.append("One labelled patterned piece provides a focal point.")
    # Shoes should belong to the occasion; a good colour match alone is not
    # enough to recommend sporty footwear for a formally labelled look.
    shoe_styles = [norm(g.get("style")) for g in garments if g.get("category") == "shoes"]
    # Occasion and seasonality use user-confirmed labels only.
    formal_occasions = {"formal", "business", "office", "work", "evening"}
    formal_styles = {"formal", "business", "smart casual", "classic"}
    relaxed_styles = {"casual", "sporty", "streetwear", "bohemian"}
    occasion_label = norm(occasion)
    if occasion_label in formal_occasions:
        if any(style in relaxed_styles for style in shoe_styles):
            score -= 18
            reasons.append("Saved shoe style may be too casual for this occasion.")
        aligned = sum(style in formal_styles for style in styles)
        if aligned:
            score += min(12, 6 * aligned)
            reasons.append("Confirmed garment styles align with your formal or work occasion.")
        if any(style in relaxed_styles for style in styles):
            score -= 7
    if climate in {"hot", "cold"}:
        # Season labels may be simple adjectives in older saved wardrobes.
        unsuitable = "cool weather" if climate == "hot" else "warm weather"
        comfortable = "warm weather" if climate == "hot" else "cool weather"
        if any(norm(g.get("season")) == unsuitable for g in garments):
            score -= 12
            reasons.append("A garment's confirmed season label may conflict with your climate preference.")
        if any(norm(g.get("season")) == comfortable for g in garments):
            score += 5
    if climate == "hot" and any(g.get("category") == "outerwear" for g in garments):
        score -= 20
    if climate == "cold" and any(g.get("category") == "outerwear" for g in garments):
        score += 12
    if not labelled:
        reasons.append("Add confirmed garment colours for better colour matching.")
    if not styles:
        reasons.append("Add confirmed styles for more personalised ranking.")
    reasons.append(f"Ranked for your {occasion} occasion and {climate} climate preference; fit and weather are unverified.")
    # Many matching labels can add up to well over 100 even though we cannot
    # verify the actual appearance or fit. Compress high additive scores into
    # an intentionally non-perfect 0-95 estimate, preserving monotonic order.
    # Negative evidence still applies before calibration.
    calibrated = (score if score <= 70 else
                  70 + 25 * (1 - math.exp(-(score - 70) / 40)))
    return {"compatibility_score": max(0, min(95, round(calibrated))),
            "compatibility_reasons": reasons[:6], "image_colour_verified": False,
            "ranking_basis": "calibrated_confirmed_wardrobe_labels_and_named_scan_swatches"}
