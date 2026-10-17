"""Bounded synthetic outfit combinations, colour harmony and truthful labels.

Only products that already passed the caller's full hard eligibility gate.
No synthetic outfit is supplier inventory, a purchase offer or Try-On input.
"""
from services.demo_outfit_variants import select_harmonised_outfit_colours
from services.demo_outfit_quality import outfit_quality

NEUTRAL = {"navy","white","cream","beige","sand","taupe","camel","grey","pearl grey","charcoal","black","brown","dark brown","denim blue","blue"}
FAMILY = {
    "blue": ("navy","blue","cobalt","denim"), "green": ("green","olive","sage"),
    "red": ("red","burgundy","coral","pink"), "warm": ("camel","tan","brown","terracotta","mustard"),
}
HOT = ("linen","cotton","silk","shorts","t-shirt","shirt","blouse","skirt","dress")
FORMAL = ("blazer","tailored","trouser","shirt","dress","loafer")
EVENING = ("dress","blazer","silk","satin","skirt","trouser","shirt")

def garment_role(p):
    t = (str(p.get("name") or "")+" "+str(p.get("category") or "")).casefold()
    if any(x in t for x in ("shoes","sneaker","loafer","boot","sandals","footwear")): return "shoes"
    if any(x in t for x in ("trouser","pants","jeans","chino","shorts","skirt","bermuda","bottom")): return "bottom"
    if any(x in t for x in ("dress","jumpsuit","abito")): return "dress"
    if any(x in t for x in ("coat","jacket","blazer","cardigan","outerwear")): return "layer"
    if any(x in t for x in ("shirt","t-shirt","blouse","top","polo","sweater","knitwear","sweatshirt")): return "top"
    return "other"

def harmony(colours):
    """Outfit-level harmony rewards restrained contrast, not identical neutrals."""
    lowered = [str(c).strip().casefold() for c in colours]
    unique = len(set(lowered))
    neutral = sum(c in NEUTRAL or c.startswith(("dark blue", "light blue")) for c in lowered)
    chromatic = [c for c in lowered if c not in NEUTRAL and not c.startswith(("dark blue","light blue"))]
    families = {k for c in chromatic for k, words in FAMILY.items() if any(w in c for w in words)}
    if unique == 1:
        return -10, "All pieces share one named colour; texture and shade contrast cannot be verified."
    if len(families) > 1 and len(chromatic) > 1:
        return -8, "Several strong colour families compete; review the combination."
    if unique == 2:
        return (11 if neutral >= 2 else 6), "Two complementary named colours create a restrained outfit."
    if len(families) <= 1 and neutral >= 1:
        return 16, "A balanced three-colour palette adds variety without competing accents."
    return 7, "The garments offer differentiated colours; check the final styling visually."

def occasion_for(items, climate):
    from services.demo_outfit_occasion import infer_occasion
    return infer_occasion(items, climate)

def make_generated_outfits(eligible_products, profile, max_results=16, demo_exploratory_colours=False):
    """Build complete three-piece looks from actual eligible in-stock garments.

    At most 48 candidates per role, sampled from the fully eligible pool.
    """
    prefs = profile.get("preferences") or {}
    climate = prefs.get("climate")
    roles = {k: [] for k in ("top","bottom","dress","shoes","layer")}
    for p in eligible_products:
        role = garment_role(p)
        if role in roles and len(roles[role]) < 48:
            roles[role].append(p)
    candidates = []
    seen = set()
    def add(parts):
        ids = tuple(str(p.get("external_id")) for p in parts)
        if len(set(ids)) != len(ids) or ids in seen: return
        seen.add(ids)
        # Do not mix men's and women's exclusive garments.
        departments = {p.get("department") for p in parts if p.get("department") in ("mens","womens")}
        if len(departments)>1: return
        seasons = {p.get("season") for p in parts if p.get("season") not in ("","All year","Tutto l'anno",None)}
        if len(seasons)>1 or (climate=="hot" and "Autunno/Inverno" in seasons) or (climate=="cold" and "Primavera/Estate" in seasons): return
        colours=select_harmonised_outfit_colours(parts, [""]*len(parts), profile, demo_exploratory_colours=demo_exploratory_colours)
        if colours is None: return
        selected=colours["colours"]
        colour_points, colour_reason = harmony(selected)
        label=occasion_for(parts,climate)
        preferred_occasion=str(prefs.get("occasion") or "").casefold()
        occasion_bonus=12 if preferred_occasion and preferred_occasion in label.casefold() else 0
        quality=outfit_quality({"occasion":"","style":""},parts,prefs)
        score=sum(float(p.get("recommendation_score") or 0) for p in parts)/len(parts)+colour_points+occasion_bonus+quality["bonus"]
        title=f"{label} · {selected[0]} and {selected[1]}"
        candidates.append({
            "id": "GEN-"+"-".join(ids), "origin":"generated", "title":title,
            "score":round(score,1),"occasion":label,"style":"",
            "alternative_colours":0,"currency":"EUR",
            "total_price":round(sum(float(p.get("price") or 0) for p in parts),2),
            "reason":f"Generated from {len(parts)} different in-stock demo garments that pass your individual eligibility rules. {colour_reason} {quality['reason']} The total is illustrative.",
            "garments":[{"name":p["name"],"category":p.get("category"),"colour_names":[c],"price":p.get("price"),"currency":"EUR"} for p,c in zip(parts,selected)]
        })
    # Rotating offsets avoid taking only the three highest-ranked garments.
    for offset in range(96):
        if roles["top"] and roles["bottom"] and roles["shoes"]:
            add([roles["top"][offset%len(roles["top"])],roles["bottom"][(offset*7)%len(roles["bottom"])],roles["shoes"][(offset*11)%len(roles["shoes"])]])
        if roles["top"] and roles["bottom"] and roles["shoes"]:
            add([roles["top"][(offset*5+1)%len(roles["top"])],roles["bottom"][(offset*11+2)%len(roles["bottom"])],roles["shoes"][(offset*13+3)%len(roles["shoes"])]])
        if roles["dress"] and roles["shoes"] and roles["layer"] and climate!="hot":
            add([roles["dress"][offset%len(roles["dress"])],roles["layer"][(offset*7)%len(roles["layer"])],roles["shoes"][(offset*11)%len(roles["shoes"])]])
    candidates.sort(key=lambda x:(-x["score"],x["id"]))
    return candidates[:max_results]
