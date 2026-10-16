"""Bounded synthetic outfit combinations, colour harmony and truthful labels.

Only products that already passed the caller's full hard eligibility gate.
No synthetic outfit is supplier inventory, a purchase offer or Try-On input.
"""
from services.demo_outfit_variants import select_outfit_colours
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
    """Prefer restrained neutral + accent outfits over competing strong colours."""
    lowered = [str(c).casefold() for c in colours]
    neutral = sum(c in NEUTRAL or c.startswith("dark blue") or c.startswith("light blue") for c in lowered)
    chromatic = [c for c in lowered if c not in NEUTRAL and not c.startswith(("dark blue","light blue"))]
    if not chromatic: return 8, "A versatile neutral colour combination."
    families = {k for c in chromatic for k,words in FAMILY.items() if any(w in c for w in words)}
    if len(chromatic) <= 1: return 12, "A neutral foundation balances one accent colour."
    if len(families) <= 1: return 9, "The accent colours belong to a related colour family."
    return -8, "The colours provide a stronger contrast."

def occasion_for(items, climate):
    words = " ".join((str(p.get("name") or "")+" "+" ".join(p.get("materials") or [])) for p in items).casefold()
    if climate == "hot" and any(x in words for x in HOT): return "Hot-weather casual"
    if any(x in words for x in FORMAL) and "blazer" in words: return "Work"
    if any(x in words for x in EVENING) and any(x in words for x in ("silk","satin","dress")): return "Evening"
    return "Casual"

def make_generated_outfits(eligible_products, profile, max_results=16):
    """Build complete three-piece looks from actual eligible in-stock garments.

    At most 24 candidates per role; no full Cartesian catalogue scan.
    """
    prefs = profile.get("preferences") or {}
    climate = prefs.get("climate")
    roles = {k: [] for k in ("top","bottom","dress","shoes","layer")}
    for p in eligible_products:
        role = garment_role(p)
        if role in roles and len(roles[role]) < 24:
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
        colours=select_outfit_colours(parts, [""]*len(parts), profile)
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
    for offset in range(24):
        if roles["top"] and roles["bottom"] and roles["shoes"]:
            add([roles["top"][offset%len(roles["top"])],roles["bottom"][(offset*7)%len(roles["bottom"])],roles["shoes"][(offset*11)%len(roles["shoes"])]])
        if roles["dress"] and roles["shoes"] and roles["layer"] and climate!="hot":
            add([roles["dress"][offset%len(roles["dress"])],roles["layer"][(offset*7)%len(roles["layer"])],roles["shoes"][(offset*11)%len(roles["shoes"])]])
    candidates.sort(key=lambda x:(-x["score"],x["id"]))
    return candidates[:max_results]
