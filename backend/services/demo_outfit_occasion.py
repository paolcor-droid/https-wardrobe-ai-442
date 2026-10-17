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

def occasion_assessment(items, climate=None, source_occasion=None):
    """Explain classification strength; confidence is heuristic, not probability."""
    label = infer_occasion(items, climate)
    text = " ".join(str(p.get("name") or "") for p in items).casefold()
    if label == "Formal":
        strong = "tuxedo" in text or ("blazer" in text and ("tailored" in text or "suit" in text))
        evidence = "Multiple formal tailoring indicators" if strong else "Limited formal indicators"
    elif label == "Business":
        strong = "blazer" in text and ("shirt" in text or "tailored" in text)
        evidence = "Blazer with professional separates" if strong else "Some professional garments"
    elif label == "Smart casual":
        strong = any(t in text for t in ("shirt", "blouse")) and any(t in text for t in ("chino", "trouser", "skirt"))
        evidence = "Shirt and smart trousers/skirt" if strong else "Mixed casual and polished pieces; dress code may vary"
    elif label == "Evening":
        strong = any(t in text for t in ("cocktail dress", "evening dress", "satin dress"))
        evidence = "Explicit eveningwear description" if strong else "Limited eveningwear evidence"
    elif label == "Hot-weather casual":
        strong = any(t in text for t in ("shorts", "linen", "sundress"))
        evidence = "Lightweight garment evidence" if strong else "Some warm-weather material clues"
    else:
        strong = any(t in text for t in ("t-shirt", "sneaker", "sweatshirt", "shorts"))
        evidence = "Everyday casual clothing" if strong else "No strong specific occasion evidence"
    confidence = "High" if strong else "Moderate" if label in ("Casual", "Smart casual") else "Low"
    source = str(source_occasion or "").strip()
    if source and source.casefold() != label.casefold():
        confidence = "Moderate" if confidence == "High" else "Low"
        evidence += "; catalogue label differs from inferred occasion"
    return {"occasion": label, "confidence": confidence, "evidence": evidence}
