"""Readable styling language for demo outfits, based only on selected garments."""
from services.demo_outfit_combinations import garment_role

def style_copy(garments, colours, occasion):
    names=[str(p.get("name") or "") for p in garments]
    labels=[str(c) for c in colours]
    distinct=list(dict.fromkeys(labels))
    shoe=next(((p,c) for p,c in zip(garments,labels) if garment_role(p)=="shoes"),None)
    main=[c for p,c in zip(garments,labels) if garment_role(p)!="shoes"]
    base=main[0] if main else distinct[0]
    accent=shoe[1] if shoe else (distinct[-1] if len(distinct)>1 else base)
    footwear=shoe[0].get("name","footwear").lower() if shoe else "accessories"
    if accent.casefold()!=base.casefold():
        title=f"{base} essentials with {accent} {footwear}"
        explanation=f"The {base} garments form a consistent foundation, while the {accent} {footwear} adds contrast."
    else:
        title=f"{base} coordinated essentials"
        explanation=f"The repeated {base} colour gives the look a consistent base."
    if occasion:
        title=f"{occasion}: {title}"
    return {"title":title,"explanation":explanation}


def diversify_outfits(outfits, limit=16):
    """Limit exact repetitions of palettes and garment groups without inventing looks."""
    remaining=list(outfits)
    picked=[]
    palette_counts={}
    names_counts={}
    while remaining and len(picked)<limit:
        def rank(o):
            colours=tuple(sorted(c.casefold() for g in o["garments"] for c in g.get("colour_names",[])))
            names=tuple(sorted(str(g.get("name") or "").casefold() for g in o["garments"]))
            return o["score"]-12*palette_counts.get(colours,0)-10*names_counts.get(names,0)
        winner=max(remaining,key=rank)
        remaining.remove(winner)
        picked.append(winner)
        colours=tuple(sorted(c.casefold() for g in winner["garments"] for c in g.get("colour_names",[])))
        names=tuple(sorted(str(g.get("name") or "").casefold() for g in winner["garments"]))
        palette_counts[colours]=palette_counts.get(colours,0)+1
        names_counts[names]=names_counts.get(names,0)+1
    return picked
