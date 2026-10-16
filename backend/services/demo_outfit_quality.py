"""Source-grounded quality signals for synthetic coordinated outfits.

Soft ranking only. Eligibility, garment references, prices and chosen colours are
validated in the caller and cannot be overridden by these signals.
"""

def outfit_quality(outfit: dict, garments: list[dict], preferences: dict) -> dict:
    """Return a modest preference bonus and conservative, verifiable reasons."""
    score = 0.0
    reasons = ["All pieces pass your saved garment and colour eligibility rules."]
    occasion = str(preferences.get("occasion") or "").strip().casefold()
    selected_occasion = str(outfit.get("occasion") or "").strip()
    style = str(preferences.get("style") or "").strip().casefold()
    selected_style = str(outfit.get("style") or "").strip()
    if occasion and selected_occasion and occasion == selected_occasion.casefold():
        score += 12
        reasons.append(f"The source outfit is labelled for {selected_occasion}.")
    if style and selected_style and style == selected_style.casefold():
        score += 8
        reasons.append(f"The source outfit matches your {selected_style} style preference.")
    climate = preferences.get("climate")
    if climate == "hot":
        from services.recommendation_engine import HOT_PREFER_TERMS
        lightweight = sum(any(t in (
            str(p.get("name") or "") + " " +
            " ".join(p.get("materials") or [])
        ).casefold() for t in HOT_PREFER_TERMS) for p in garments)
        if lightweight:
            score += min(6, 2 * lightweight)
            reasons.append(f"{lightweight} piece(s) mention lightweight-favoured materials or garment types.")
    return {"bonus": score, "reason": " ".join(reasons)}
