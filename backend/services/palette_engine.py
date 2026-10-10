from __future__ import annotations
from typing import Dict, List

COLOURS = {
    "ivory": ("Ivory", "#F4E8D0"), "soft_white": ("Soft White", "#F5F1E8"),
    "warm_beige": ("Warm Beige", "#CDB79E"), "camel": ("Camel", "#B58B5A"),
    "mushroom": ("Mushroom", "#A99B8E"), "cocoa": ("Cocoa", "#6F5144"),
    "chocolate": ("Chocolate", "#4B342B"), "soft_navy": ("Soft Navy", "#35445A"),
    "charcoal": ("Charcoal", "#414247"), "cool_taupe": ("Cool Taupe", "#9B918C"),
    "pearl": ("Pearl", "#E9E6E1"), "black": ("Black", "#171717"),
    "peach": ("Peach", "#E9A17B"), "coral": ("Coral", "#D96B5F"),
    "terracotta": ("Terracotta", "#B65F45"), "olive": ("Olive", "#727442"),
    "forest": ("Forest Green", "#31533F"), "warm_green": ("Fresh Green", "#5E8C4A"),
    "turquoise": ("Turquoise", "#2F9C9A"), "deep_teal": ("Deep Teal", "#1F6262"),
    "mustard": ("Mustard", "#C59A32"), "dusty_coral": ("Dusty Coral", "#C47B72"),
    "sage": ("Sage", "#8E9B7B"), "rose": ("Soft Rose", "#C98D9A"),
    "berry": ("Berry", "#8E3E5C"), "cobalt": ("Cobalt", "#3157A4"),
    "icy_blue": ("Icy Blue", "#BFD5E8"), "blue_red": ("Blue Red", "#A72E42"),
    "lavender": ("Lavender", "#9B8BB4"), "emerald": ("Emerald", "#247052"),
}

def _items(keys: List[str]) -> List[Dict[str, str]]:
    return [{"name": COLOURS[k][0], "hex": COLOURS[k][1]} for k in keys]

def suggested_season(undertone: str, depth: str, chroma: str, contrast: str) -> str:
    """Styling shorthand derived consistently from the four palette dimensions."""
    warm = undertone in {"warm", "neutral_warm"}
    cool = undertone in {"cool", "neutral_cool"}
    if not warm and not cool:
        warm = depth == "medium" and contrast != "high"
    if warm:
        return "spring" if chroma == "clear" or (chroma == "balanced" and depth == "light" and contrast != "low") else "autumn"
    return "winter" if chroma == "clear" or (chroma == "balanced" and depth == "deep" and contrast == "high") else "summer"


def build_palette(undertone: str, depth: str, chroma: str, contrast: str) -> dict:
    """Deterministic styling palette: undertone, depth, chroma and contrast all matter."""
    warm = undertone in {"warm", "neutral_warm"}
    cool = undertone in {"cool", "neutral_cool"}
    if warm:
        if chroma == "clear":
            accents = ["peach", "coral", "turquoise", "warm_green"]
        elif chroma == "muted":
            accents = ["olive", "deep_teal", "terracotta", "dusty_coral"]
        else:
            accents = ["sage", "coral", "deep_teal", "warm_green"]
        neutrals = ["ivory", "warm_beige", "camel", "soft_navy"]
        caution = ["soft_white", "charcoal", "icy_blue"]
    elif cool:
        if chroma == "clear":
            accents = ["cobalt", "emerald", "blue_red", "icy_blue"]
        elif chroma == "muted":
            accents = ["rose", "berry", "lavender", "deep_teal"]
        else:
            accents = ["rose", "emerald", "cobalt", "lavender"]
        neutrals = ["soft_white", "cool_taupe", "soft_navy", "charcoal"]
        caution = ["ivory", "camel", "mustard"]
    else:
        if chroma == "clear":
            accents = ["turquoise", "cobalt", "emerald", "coral"]
        elif chroma == "muted":
            accents = ["sage", "rose", "deep_teal", "berry"]
        else:
            accents = ["deep_teal", "rose", "emerald", "berry"]
        neutrals = ["soft_white", "mushroom", "soft_navy", "charcoal"]
        caution = ["mustard", "icy_blue", "terracotta"]

    # Depth changes the recommended lightness of both neutrals and accents.
    if depth == "light":
        neutrals = (["ivory", "warm_beige", "mushroom", "camel"] if warm
                    else ["soft_white", "pearl", "cool_taupe", "mushroom"])
        accents = (["peach", "sage", "dusty_coral", "warm_green"] if warm and chroma != "clear"
                   else ["peach", "coral", "turquoise", "warm_green"] if warm
                   else ["rose", "lavender", "icy_blue", "sage"] if chroma != "clear"
                   else ["icy_blue", "turquoise", "lavender", "emerald"])
    elif depth == "deep":
        neutrals = (["chocolate", "cocoa", "soft_navy", "ivory"] if warm
                    else ["charcoal", "black", "soft_navy", "pearl"])
        accents = (["forest", "deep_teal", "terracotta", "mustard"] if warm and chroma != "clear"
                   else ["emerald", "turquoise", "coral", "mustard"] if warm
                   else ["berry", "deep_teal", "emerald", "cobalt"] if chroma != "clear"
                   else ["cobalt", "emerald", "blue_red", "turquoise"])

    # Contrast changes combinations, not just the statement-colour order.
    if contrast == "low":
        neutrals = [k for k in neutrals if k not in {"black", "charcoal", "chocolate", "soft_navy"}]
        for k in (["warm_beige", "mushroom", "ivory", "cocoa"] if warm
                  else ["pearl", "mushroom", "cool_taupe", "soft_white"]):
            if len(neutrals) >= 4:
                break
            if k not in neutrals:
                neutrals.append(k)
        statement = accents[1:3]
    elif contrast == "high":
        contrast_neutral = "chocolate" if warm else "charcoal"
        if contrast_neutral not in neutrals:
            neutrals[-1] = contrast_neutral
        statement = accents[:2]
    else:
        statement = accents[0:2] if chroma == "clear" else accents[1:3]

    return {
        "best_neutrals": _items(neutrals),
        "best_accents": _items(accents),
        "statement_colours": _items(statement),
        "caution_colours": _items(caution),
    }
