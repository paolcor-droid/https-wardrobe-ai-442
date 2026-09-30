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
    text = " ".join([
        product.get("name", ""), product.get("description", ""), product.get("category", ""),
        " ".join(product.get("materials", []) or []),
    ]).lower()
    return not any(term in text for term in HOT_EXCLUDE_TERMS)

def _coarse_undertone(undertone: str) -> str:
    return "warm" if "warm" in undertone else "cool" if "cool" in undertone else "neutral"

def _norm_colour(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").replace("-", " ").split())

def _swatch_names(colour_profile: dict, key: str) -> set[str]:
    return {
        _norm_colour(item.get("name", ""))
        for item in (colour_profile.get(key) or [])
        if isinstance(item, dict) and item.get("name")
    }

def _product_colour_names(product: dict) -> set[str]:
    values = product.get("colour_names", product.get("color_names", [])) or []
    return {_norm_colour(str(value)) for value in values if value}

def _colour_match(product_names: set[str], palette_names: set[str]) -> set[str]:
    matches: set[str] = set()
    for product_name in product_names:
        for palette_name in palette_names:
            if product_name == palette_name or product_name in palette_name or palette_name in product_name:
                matches.add(palette_name)
    return matches

def scan_colour_evidence(product: dict, colour_profile: dict | None) -> dict:
    """Return named-colour evidence from the actual saved Your Scan palette."""
    if not colour_profile:
        return {"best_neutrals": set(), "best_accents": set(), "statement_colours": set(), "caution_colours": set()}
    product_names = _product_colour_names(product)
    return {
        key: _colour_match(product_names, _swatch_names(colour_profile, key))
        for key in ("best_neutrals", "best_accents", "statement_colours", "caution_colours")
    }

def recommendation_score(product: dict, colour_profile: dict | None, occasion: str | None, budget_max: float | None, climate: str | None, style: str | None = None, preferred_colours: list[str] | None = None, avoided_colours: list[str] | None = None) -> float:
    price = product.get("price")
    if budget_max is not None and price is not None and price > budget_max:
        return -1
    product_occasions = product.get("occasions", []) or []
    # Missing occasion metadata means unknown, not unsuitable. Reject only when
    # the source explicitly classifies the product for other occasions.
    if occasion and product_occasions and occasion not in product_occasions:
        return -1
    if climate == "hot" and not is_hot_weather_suitable(product):
        return -1

    score = 0.0
    evidence = scan_colour_evidence(product, colour_profile)
    if colour_profile:
        # Named colours produced by Your Scan are stronger evidence than broad undertone tags.
        if evidence["best_accents"]:
            score += 34
        if evidence["best_neutrals"]:
            score += 28
        if evidence["statement_colours"]:
            score += 10
        if evidence["caution_colours"]:
            score -= 30

        # Fallback for provider records whose colour name is too generic to match a scan swatch.
        if not any(evidence.values()):
            coarse = _coarse_undertone(colour_profile.get("undertone", "neutral"))
            tags = product.get("palette_tags", [])
            score += 18 if coarse in tags else 8 if "neutral" in tags else 0
    else:
        score += 20

    score += 25 if not occasion or occasion in product_occasions else 0
    score += 15 if climate != "hot" or is_hot_weather_suitable(product) else 0
    text = " ".join([
        product.get("name", ""), product.get("description", ""),
        " ".join(product.get("colour_names", product.get("color_names", []))),
        " ".join(product.get("materials", []) or []),
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
    if budget_max and price is not None:
        score += max(0, 10 * (1 - price / max(budget_max, 1)))
    return round(score, 1)

def recommendation_reasons(product: dict, colour_profile: dict | None, occasion: str | None, climate: str | None, style: str | None = None, preferred_colours: list[str] | None = None, avoided_colours: list[str] | None = None) -> list[str]:
    reasons: list[str] = []
    evidence = scan_colour_evidence(product, colour_profile)
    if colour_profile:
        if evidence["best_accents"]:
            colour = sorted(evidence["best_accents"])[0].title()
            reasons.append(f"{colour} is one of the accent colours recommended by your skin analysis.")
        elif evidence["best_neutrals"]:
            colour = sorted(evidence["best_neutrals"])[0].title()
            reasons.append(f"{colour} is one of the neutrals recommended by your skin analysis.")
        elif evidence["statement_colours"]:
            colour = sorted(evidence["statement_colours"])[0].title()
            reasons.append(f"{colour} is one of the statement colours recommended by your skin analysis.")
        elif evidence["caution_colours"]:
            colour = sorted(evidence["caution_colours"])[0].title()
            reasons.append(f"Note: {colour} appears in the caution colours from your skin analysis.")
        else:
            coarse = _coarse_undertone(colour_profile.get("undertone", "neutral"))
            if coarse in product.get("palette_tags", []):
                reasons.append(f"Its colour family harmonises with your {colour_profile.get('undertone', 'neutral').replace('_', '-')} colour profile.")
            elif "neutral" in product.get("palette_tags", []):
                reasons.append("Its neutral colour is compatible with your analysed palette.")

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
