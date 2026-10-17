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


def select_harmonised_outfit_colours(products: list[dict], original: list[str], profile: dict) -> dict | None:
    """Choose a complete, stocked, profile-eligible palette rather than each colour alone.

    A bounded beam explores colour variants without fabricating stock or relaxing
    the colour gate. Source XML colours are a small tie-breaker, not a hard lock.
    """
    from services.demo_outfit_combinations import harmony
    if len(products) != len(original):
        return None
    prefs = profile.get("preferences") or {}
    preferred = {_norm_colour(str(c)) for c in prefs.get("preferred_colours") or []}
    choices = []
    for product in products:
        acceptable = [str(c) for c in (product.get("colour_names") or [])
                      if is_colour_eligible({**product, "colour_names": [str(c)]},
                         profile.get("skin"), prefs.get("preferred_colours"), prefs.get("avoided_colours"))]
        if not acceptable:
            return None
        choices.append(acceptable[:16])
    beams = [([], 0)]
    for index, options in enumerate(choices):
        next_beams = []
        for colours, bonus in beams:
            for colour in options:
                preference = 1.5 if _colour_match({_norm_colour(colour)}, preferred) else 0
                source = 0.5 if colour == original[index] else 0
                next_beams.append((colours + [colour], bonus + preference + source))
        # Encourage meaningful partial palette variety without eliminating
        # low-contrast options when they are the only eligible choices.
        next_beams.sort(key=lambda v: (
            -(v[1] + 3 * len(set(c.casefold() for c in v[0]))), tuple(v[0])))
        beams = next_beams[:128]
    winner = max(beams, key=lambda v: (
        harmony(v[0])[0] + v[1], tuple(v[0])))
    selected = winner[0]
    return {"colours": selected, "substituted": sum(
        bool(source) and chosen != source for source, chosen in zip(original, selected))}
