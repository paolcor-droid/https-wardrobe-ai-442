"""Conservative explainable ranking of *owned* garments using confirmed labels.

No image-colour inference, no live weather and no skin-type assumptions.
Scores compare garments within a user's own wardrobe; not probabilities.
"""
from __future__ import annotations

import re
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
    requested_style = norm(preferred_style)
    if requested_style and styles:
        matching = sum(style == requested_style for style in styles)
        score += 14 * matching
        if matching:
            reasons.append(f"{matching} garment(s) match your preferred {requested_style} style.")
    if len(styles) > 1 and len(set(styles)) == 1:
        score += 10
        reasons.append("The saved garment styles are consistent.")
    if climate == "hot" and any(g.get("category") == "outerwear" for g in garments):
        score -= 20
    if climate == "cold" and any(g.get("category") == "outerwear" for g in garments):
        score += 12
    if not labelled:
        reasons.append("Add confirmed garment colours for better colour matching.")
    if not styles:
        reasons.append("Add confirmed styles for more personalised ranking.")
    reasons.append(f"Ranked for your {occasion} occasion and {climate} climate preference; fit and weather are unverified.")
    return {"compatibility_score": max(0, min(100, score)),
            "compatibility_reasons": reasons[:6], "image_colour_verified": False,
            "ranking_basis": "confirmed_wardrobe_labels_and_named_scan_swatches"}
