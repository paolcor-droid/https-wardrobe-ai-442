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

COLOUR_EQUIVALENTS = {
    "navy blue": {"soft navy", "navy"},
    "navy": {"navy blue", "soft navy"},
    "soft navy": {"navy", "navy blue"},
    "rose": {"soft rose"},
    "soft rose": {"rose"},
}


def _colour_match(product_names: set[str], palette_names: set[str]) -> set[str]:
    """Match exact colour names or explicitly recognised equivalents."""
    matches: set[str] = set()

    for product_name in product_names:
        for palette_name in palette_names:
            if (
                product_name == palette_name
                or palette_name in COLOUR_EQUIVALENTS.get(product_name, set())
            ):
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
    """Explain recommendations using verified garment colour evidence."""
    reasons: list[str] = []
    product_colours = _product_colour_names(product)
    evidence = scan_colour_evidence(product, colour_profile)

    preferred = {
        _norm_colour(str(c))
        for c in (preferred_colours or [])
        if c
    }
    preferred_matches = _colour_match(product_colours, preferred)

    if preferred_matches:
        colour = sorted(preferred_matches)[0].title()
        reasons.append(
            f"This garment matches {colour}, one of your preferred clothing colours."
        )

    for key, label in (
        ("best_accents", "accent"),
        ("best_neutrals", "neutral"),
        ("statement_colours", "statement"),
    ):
        matches = evidence[key]
        if matches:
            colour = sorted(matches)[0].title()
            article = "an" if label == "accent" else "a"
            reasons.append(
                f"Its verified colour matches {colour}, {article} {label} colour recommended by your skin analysis."
            )
            break

    if occasion and occasion in (product.get("occasions") or []):
        reasons.append(f"It is suitable for your {occasion} occasion.")

    text = " ".join([
        product.get("name", ""),
        product.get("description", ""),
        " ".join(product.get("colour_names", product.get("color_names", [])) or []),
    ]).lower()

    if climate == "hot" and is_hot_weather_suitable(product):
        if any(term in text for term in HOT_PREFER_TERMS):
            reasons.append("Its product description indicates a lightweight option for hot weather.")
        else:
            reasons.append("It passes your hot-weather clothing filters.")

    if style and any(term in text for term in STYLE_TERMS.get(style, ())):
        reasons.append(f"It also aligns with your {style} style preference.")

    return reasons[:3] or [
        "This garment meets your selected colour and shopping filters."
    ]


def is_colour_eligible(
    product: dict,
    colour_profile: dict | None,
    preferred_colours: list[str] | None = None,
    avoided_colours: list[str] | None = None,
) -> bool:
    """Apply strict colour eligibility using verified garment colour names."""
    product_colours = _product_colour_names(product)
    if not product_colours:
        return False

    avoided = {
        _norm_colour(str(c))
        for c in (avoided_colours or [])
        if c
    }
    if avoided and _colour_match(product_colours, avoided):
        return False

    preferred = {
        _norm_colour(str(c))
        for c in (preferred_colours or [])
        if c
    }
    if preferred and _colour_match(product_colours, preferred):
        return True

    if colour_profile:
        evidence = scan_colour_evidence(product, colour_profile)
        return any(
            evidence[key]
            for key in ("best_neutrals", "best_accents", "statement_colours")
        )

    # Without a scan or explicit preferred colours, no colour match is verified.
    return False
