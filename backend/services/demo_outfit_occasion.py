"""Conservative outfit-level occasion labels grounded in garment roles and names.

Never infer a formal dress code from price, brand, or a single accessory.
"""
from services.demo_outfit_combinations import garment_role

def infer_occasion(items, climate=None):
    words=" ".join(str(p.get("name") or "")+" "+" ".join(p.get("materials") or []) for p in items).casefold()
    roles={garment_role(p) for p in items}
    tailored=any(x in words for x in ("tailored","sartorial","suit","tuxedo","formal"))
    blazer=any(x in words for x in ("blazer","structured jacket"))
    smart_bottom=any(x in words for x in ("chino","trouser","tailored","skirt"))
    shirt=any(x in words for x in ("shirt","blouse","camicia")) and not "t-shirt" in words
    casual_top=any(x in words for x in ("t-shirt","sweatshirt","hoodie","tee "))
    formal_shoes=any(x in words for x in ("oxford","derby","dress shoes","heel"))
    loafers="loafer" in words
    sneakers=any(x in words for x in ("sneaker","trainer","canvas shoes"))
    evening=any(x in words for x in ("evening dress","cocktail dress","sequins","satin dress"))
    if evening and ("dress" in roles or "dress" in words):
        return "Evening"
    if (tailored and blazer and (formal_shoes or "dress" in roles)) or ("tuxedo" in words):
        return "Formal"
    if blazer and (shirt or tailored or smart_bottom) and not casual_top:
        return "Business"
    if smart_bottom and (shirt or loafers or blazer) and not sneakers:
        return "Smart casual"
    if climate=="hot" and any(x in words for x in ("linen","shorts","cotton","sundress")):
        return "Hot-weather casual"
    return "Casual"
