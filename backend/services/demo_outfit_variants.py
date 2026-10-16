"""Choose stock-backed demo colour variants without weakening saved restrictions."""
from services.recommendation_engine import is_colour_eligible, _colour_match, _norm_colour

def select_outfit_colours(products: list[dict], original: list[str], profile: dict) -> dict | None:
    """Retain a source colour where valid; otherwise prefer verified in-stock variants.

    Input product colour_names come exclusively from in-stock XML variants.
    Returns None when any piece lacks an acceptable colour.
    """
    if len(products) != len(original):
        return None
    prefs = profile.get("preferences") or {}
    preferred = {_norm_colour(str(c)) for c in prefs.get("preferred_colours") or []}
    selected = []
    substituted = 0
    for product, original_colour in zip(products, original):
        candidates = product.get("colour_names") or []
        acceptable = [str(colour) for colour in candidates if is_colour_eligible(
            {**product, "colour_names": [str(colour)]},
            profile.get("skin"), prefs.get("preferred_colours"), prefs.get("avoided_colours")
        )]
        if not acceptable:
            return None
        if original_colour in acceptable:
            chosen = original_colour
        else:
            chosen = max(acceptable, key=lambda c: (
                bool(_colour_match({_norm_colour(c)}, preferred)), -acceptable.index(c)
            ))
            substituted += 1
        selected.append(chosen)
    return {"colours": selected, "substituted": substituted}
