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

def build_palette(undertone: str, depth: str, chroma: str, contrast: str) -> dict:
    warm = undertone in {"warm", "neutral_warm"}
    cool = undertone in {"cool", "neutral_cool"}
    if warm:
        neutrals = ["ivory", "warm_beige", "camel", "soft_navy"]
        accents = ["peach", "coral", "turquoise", "warm_green"] if chroma == "clear" else ["olive", "deep_teal", "terracotta", "dusty_coral"]
        caution = ["soft_white", "charcoal", "icy_blue"]
    elif cool:
        neutrals = ["soft_white", "cool_taupe", "soft_navy", "charcoal"]
        accents = ["cobalt", "emerald", "blue_red", "icy_blue"] if chroma == "clear" else ["rose", "berry", "lavender", "deep_teal"]
        caution = ["ivory", "camel", "mustard"]
    else:
        neutrals = ["soft_white", "mushroom", "soft_navy", "charcoal"]
        accents = ["deep_teal", "rose", "emerald", "berry"] if chroma != "clear" else ["turquoise", "cobalt", "emerald", "coral"]
        caution = ["mustard", "icy_blue", "terracotta"]

    if depth == "deep":
        neutrals = ["chocolate" if warm else "charcoal", "soft_navy", "cocoa" if warm else "black", "ivory" if warm else "soft_white"]
        accents = ["forest" if warm else "emerald", "deep_teal", "terracotta" if warm else "berry", "mustard" if warm else "cobalt"]
    elif depth == "light":
        neutrals = ["ivory" if warm else "soft_white", "warm_beige" if warm else "pearl", "camel" if warm else "cool_taupe", "soft_navy"]
    statement = accents[:2] if contrast == "high" or chroma == "clear" else accents[1:3]
    return {"best_neutrals": _items(neutrals), "best_accents": _items(accents), "statement_colours": _items(statement), "caution_colours": _items(caution)}
