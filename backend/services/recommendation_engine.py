from __future__ import annotations

HOT_EXCLUDE_TERMS = ("wool", "puffer", "overcoat", "heavy", "cashmere", "merino", "leather jacket", "blazer")
HOT_PREFER_TERMS = ("linen", "cotton", "silk", "sundress", "shorts", "camisole", "tee")

def is_hot_weather_suitable(product: dict) -> bool:
    text = " ".join([product.get("name", ""), product.get("description", ""), product.get("category", "")]).lower()
    return not any(term in text for term in HOT_EXCLUDE_TERMS)

def recommendation_score(product: dict, colour_profile: dict | None, occasion: str | None, budget_max: float | None, climate: str | None) -> float:
    if budget_max is not None and product.get("price", 0) > budget_max:
        return -1
    if occasion and occasion not in product.get("occasions", []):
        return -1
    if climate == "hot" and not is_hot_weather_suitable(product):
        return -1

    score = 0.0
    if colour_profile:
        undertone = colour_profile.get("undertone", "neutral")
        coarse = "warm" if "warm" in undertone else "cool" if "cool" in undertone else "neutral"
        tags = product.get("palette_tags", [])
        score += 40 if coarse in tags else 18 if "neutral" in tags else 0
    else:
        score += 20
    score += 25 if not occasion or occasion in product.get("occasions", []) else 0
    score += 15 if climate != "hot" or is_hot_weather_suitable(product) else 0
    text = " ".join([product.get("name", ""), product.get("description", "")]).lower()
    if climate == "hot" and any(t in text for t in HOT_PREFER_TERMS):
        score += 8
    if budget_max:
        score += max(0, 10 * (1 - product.get("price", 0) / max(budget_max, 1)))
    return round(score, 1)
