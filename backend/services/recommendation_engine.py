from __future__ import annotations

HOT_EXCLUDE_TERMS = ("wool", "puffer", "overcoat", "heavy", "cashmere", "merino", "leather jacket", "blazer", "fedora")
HOT_PREFER_TERMS = ("linen", "cotton", "silk", "sundress", "shorts", "camisole", "tee")
STYLE_TERMS = {
    "classic": ("tailored", "shirt", "trouser", "loafer", "trench"),
    "relaxed": ("linen", "denim", "cargo", "tee", "sneaker"),
    "minimal": ("minimal", "clean", "poplin", "column", "structured"),
    "romantic": ("silk", "satin", "pleated", "dress", "scarf"),
    "bold": ("leather", "cobalt", "dramatic", "party", "blazer"),
}

def is_hot_weather_suitable(product: dict) -> bool:
    text = " ".join([product.get("name", ""), product.get("description", ""), product.get("category", "")]).lower()
    return not any(term in text for term in HOT_EXCLUDE_TERMS)

def _coarse_undertone(undertone: str) -> str:
    return "warm" if "warm" in undertone else "cool" if "cool" in undertone else "neutral"

def recommendation_score(product: dict, colour_profile: dict | None, occasion: str | None, budget_max: float | None, climate: str | None, style: str | None = None, preferred_colours: list[str] | None = None, avoided_colours: list[str] | None = None) -> float:
    if budget_max is not None and product.get("price", 0) > budget_max:
        return -1
    if occasion and occasion not in product.get("occasions", []):
        return -1
    if climate == "hot" and not is_hot_weather_suitable(product):
        return -1

    score = 0.0
    if colour_profile:
        coarse = _coarse_undertone(colour_profile.get("undertone", "neutral"))
        tags = product.get("palette_tags", [])
        score += 40 if coarse in tags else 18 if "neutral" in tags else 0
    else:
        score += 20
    score += 25 if not occasion or occasion in product.get("occasions", []) else 0
    score += 15 if climate != "hot" or is_hot_weather_suitable(product) else 0
    text = " ".join([
        product.get("name", ""), product.get("description", ""),
        " ".join(product.get("colour_names", product.get("color_names", []))),
    ]).lower()
    preferred = [c.lower() for c in (preferred_colours or [])]
    avoided = [c.lower() for c in (avoided_colours or [])]
    if any(c in text for c in avoided):
        score -= 35
    if any(c in text for c in preferred):
        score += 8
    if climate == "hot" and any(t in text for t in HOT_PREFER_TERMS):
        score += 8
    if style and any(t in text for t in STYLE_TERMS.get(style, ())):
        score += 10
    if budget_max:
        score += max(0, 10 * (1 - product.get("price", 0) / max(budget_max, 1)))
    return round(score, 1)

def recommendation_reasons(product: dict, colour_profile: dict | None, occasion: str | None, climate: str | None, style: str | None = None, preferred_colours: list[str] | None = None, avoided_colours: list[str] | None = None) -> list[str]:
    reasons: list[str] = []
    if colour_profile:
        coarse = _coarse_undertone(colour_profile.get("undertone", "neutral"))
        if coarse in product.get("palette_tags", []):
            reasons.append(f"Its colour family harmonises with your {colour_profile.get('undertone', 'neutral').replace('_', '-')} colour profile.")
        elif "neutral" in product.get("palette_tags", []):
            reasons.append("Its neutral colour makes it versatile with your analysed palette.")
    if occasion and occasion in product.get("occasions", []):
        reasons.append(f"It is suitable for your {occasion} occasion.")
    text = " ".join([
        product.get("name", ""), product.get("description", ""),
        " ".join(product.get("colour_names", product.get("color_names", []))),
    ]).lower()
    preferred_matches = [c for c in (preferred_colours or []) if c.lower() in text]
    avoided_matches = [c for c in (avoided_colours or []) if c.lower() in text]
    if preferred_matches:
        reasons.append(f"It includes {preferred_matches[0]}, one of your preferred clothing colours.")
    if avoided_matches:
        reasons.append(f"Note: it includes {avoided_matches[0]}, which you asked LUMIÈRE to avoid.")
    if climate == "hot" and is_hot_weather_suitable(product):
        if any(t in text for t in HOT_PREFER_TERMS):
            reasons.append("Its lightweight style is a stronger choice for hot weather.")
        else:
            reasons.append("It avoids the heavy layers excluded from your hot-weather edit.")
    if style and any(t in text for t in STYLE_TERMS.get(style, ())):
        reasons.append(f"It also aligns with your {style} style preference.")
    return reasons[:3] or ["This piece fits the active wardrobe filters."]
