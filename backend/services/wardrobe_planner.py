"""Deterministic, explainable wardrobe outfit and capsule planning.

No live weather, inventory, purchase or fit claims. Suggestions use the user's
saved wardrobe labels; they do not infer garment colours from photographs.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json


def _items(items):
    return [dict(item) for item in items if item.get("id") and item.get("name") and not item.get("deleted_at")]


def _feedback_adjustments(items, feedback):
    """Prepare bounded, account-supplied signals from previously rated owned looks.

    Only currently owned item IDs are used; there is no global or cross-account
    training. Matching a full saved combination has more weight than simply
    sharing a garment or a confirmed colour/style label.
    """
    by_id = {item["id"]: item for item in items}
    signals = []
    legacy_signals = {}
    for row in (feedback or []):
        if not isinstance(row, dict) or not str(row.get("product_id", "")).startswith("owned-outfit:"):
            continue
        ids = row.get("wardrobe_item_ids")
        sentiment = row.get("sentiment")
        if sentiment not in {"liked", "saved", "disliked"}:
            continue
        if ids is None:
            # Older feedback records stored only the salted-free digest of
            # sorted owned IDs. Match those to the exact look, never infer
            # which garment IDs were rated or generalise to other looks.
            digest = row["product_id"].removeprefix("owned-outfit:")
            if len(digest) == 64 and all(c in "0123456789abcdef" for c in digest):
                legacy_signals[digest] = sentiment
            continue
        if (not isinstance(ids, list) or not 1 <= len(ids) <= 5 or
                len(set(str(value) for value in ids)) != len(ids) or
                any(not isinstance(value, str) or value not in by_id for value in ids)):
            continue
        signals.append((set(ids), sentiment))
    # Keep behaviour deterministic even with large feedback histories.
    return by_id, signals[-100:], legacy_signals


def _feedback_delta(look_ids, by_id, signals, legacy_signals):
    from services.wardrobe_compatibility import norm
    if not signals and not legacy_signals:
        return 0
    look = set(look_ids)
    digest = hashlib.sha256(json.dumps(sorted(look_ids)).encode()).hexdigest()
    legacy_sentiment = legacy_signals.get(digest)
    positives, negatives = [], []
    for rated_ids, sentiment in signals:
        if look == rated_ids:
            adjustment = {"liked": 14, "saved": 18, "disliked": -24}[sentiment]
        else:
            overlap = len(look & rated_ids) / max(1, len(look | rated_ids))
            # Learn a little from similar confirmed garment types/labels,
            # without treating unrelated looks as user preferences.
            label_similarity = 0
            for item_id in look - rated_ids:
                garment = by_id[item_id]
                for rated_id in rated_ids - look:
                    rated = by_id[rated_id]
                    if garment.get("category") != rated.get("category"):
                        continue
                    if (norm(garment.get("colour")) and
                            norm(garment.get("colour")) == norm(rated.get("colour"))):
                        label_similarity = max(label_similarity, 0.25)
                    if (norm(garment.get("style")) and
                            norm(garment.get("style")) == norm(rated.get("style"))):
                        label_similarity = max(label_similarity, 0.15)
            similarity = max(overlap, label_similarity)
            adjustment = round(similarity * (9 if sentiment in {"liked", "saved"} else -12))
        if adjustment > 0:
            positives.append(adjustment)
        elif adjustment < 0:
            negatives.append(adjustment)
    if legacy_sentiment is not None:
        # The current record format supersedes legacy digest-only records.
        # A legacy exact match is still stronger than similar-outfit hints.
        exact_delta = {"liked": 14, "saved": 18, "disliked": -24}[legacy_sentiment]
        if not any(rated_ids == look for rated_ids, _ in signals):
            return exact_delta
    # A single repeated tap or many similar looks cannot overpower a strong
    # avoided-colour or weather penalty. Exact dislikes remain meaningful.
    return max(-24, min(18, (max(positives) if positives else 0) +
                        (min(negatives) if negatives else 0)))


def plan_outfits(items, occasion="casual", climate="mild", limit=12, *,
                 scan=None, preferred_colours=None, avoided_colours=None, preferred_style=None,
                 feedback=None):
    """Rank owned combinations by labelled colour, style and saved-scan evidence.

    Use a bounded candidate pool; do not read garment pixels or infer fabric/fit.
    Preserve variety of owned shoes when there is just one base outfit.
    """
    from services.wardrobe_compatibility import score_owned_outfit
    if not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    items = _items(items)
    feedback_items, feedback_signals, legacy_feedback = _feedback_adjustments(items, feedback)
    tops = [x for x in items if x.get("category") == "top"]
    bottoms = [x for x in items if x.get("category") == "bottom"]
    dresses = [x for x in items if x.get("category") == "dress"]
    shoes = [x for x in items if x.get("category") == "shoes"]
    outer = [x for x in items if x.get("category") == "outerwear"]
    accessories = [x for x in items if x.get("category") == "accessory"]
    # Bound work and avoid a 200-item wardrobe producing millions of sets.
    bases = ([[top, bottom] for top in tops for bottom in bottoms] +
             [[dress] for dress in dresses])[:1200]
    outfits = []
    seen = set()
    def composition_score(garments):
        return score_owned_outfit(
            garments, scan=scan, preferred_colours=preferred_colours,
            avoided_colours=avoided_colours, preferred_style=preferred_style,
            occasion=occasion, climate=climate)["compatibility_score"]

    for index, base in enumerate(bases):
        # Choose footwear for the actual top/bottom (or dress) combination,
        # rather than the first four uploads in arbitrary wardrobe order.
        # Preserve alternatives if a user owns multiple suitable pairs.
        shoe_options = sorted(
            shoes, key=lambda shoe: -composition_score(base + [shoe]))[:4] if shoes else [None]
        for shoe in shoe_options:
            chosen = list(base)
            if shoe:
                chosen.append(shoe)
            if climate == "cold" and outer:
                # The previous round-robin ignored outerwear colour and style.
                # Choose the most compatible available layer for this outfit.
                layer = max(outer, key=lambda item: composition_score(chosen + [item]))
                chosen.append(layer)
            # Keep owned accessories optional in meaning; prefer the accessory
            # that suits the particular look over the first uploaded item.
            if accessories:
                accessory = max(accessories, key=lambda item: composition_score(chosen + [item]))
                chosen.append(accessory)
            ids = tuple(x["id"] for x in chosen)
            if ids in seen:
                continue
            seen.add(ids)
            names = [x["name"] for x in chosen]
            evidence = score_owned_outfit(
                chosen, scan=scan, preferred_colours=preferred_colours,
                avoided_colours=avoided_colours, preferred_style=preferred_style,
                occasion=occasion, climate=climate)
            # Distinguish a styled base combination from a fully ready outfit.
            # Accessories are optional; footwear and cold-weather layers are
            # clearly marked as missing, not silently treated as "complete".
            missing = []
            if not shoe:
                missing.append("shoes")
            if climate == "cold" and not any(g.get("category") == "outerwear" for g in chosen):
                missing.append("outerwear")
            feedback_delta = _feedback_delta(ids, feedback_items, feedback_signals, legacy_feedback)
            # Preserve the full internal order even when the user-facing,
            # calibrated score approaches its 95-point display ceiling.
            personalised_rank_score = evidence["compatibility_score"] + feedback_delta
            evidence["compatibility_score"] = max(
                0, min(95, personalised_rank_score))
            if feedback_delta:
                evidence["compatibility_reasons"].append(
                    "Your saved outfit feedback influenced this ranking.")
            outfits.append({
                "item_ids": list(ids), "names": names,
                "reason": " ".join(evidence["compatibility_reasons"]),
                "feedback_adjustment": feedback_delta,
                "personalised_rank_score": personalised_rank_score,
                "missing_categories": missing,
                "is_complete": not missing,
                **evidence,
            })
    # Diversify the ranked set so one high-scoring shirt cannot consume all slots.
    # Always keep the highest-ranked look; use a small repetition penalty afterwards.
    ranked = sorted(outfits, key=lambda row: -row["personalised_rank_score"])
    selected = []
    used = Counter()
    visible_combinations = set()
    by_id = {item["id"]: item for item in items}
    while ranked and len(selected) < limit:
        index = max(range(len(ranked)), key=lambda i: (
            ranked[i]["personalised_rank_score"] -
            sum(9 * used[item_id] for item_id in ranked[i]["item_ids"]),
            -i))
        choice = ranked.pop(index)
        # Different uploads with the same garment labels can otherwise make
        # indistinguishable recommendations. Preserve distinct colours/styles.
        signature = tuple(
            (str(by_id[item_id].get("category") or "").casefold(),
             " ".join(str(by_id[item_id].get("name") or "").casefold().split()),
             " ".join(str(by_id[item_id].get("colour") or "").casefold().split()),
             " ".join(str(by_id[item_id].get("style") or "").casefold().split()))
            for item_id in choice["item_ids"]
        )
        if signature in visible_combinations:
            continue
        visible_combinations.add(signature)
        selected.append(choice)
        used.update(choice["item_ids"])
    return selected

def wardrobe_insights(items):
    """Explain potential wardrobe duplication using user-entered labels only.

    Never infer garment similarity, condition or fit from photographs.
    """
    items = _items(items)
    groups = {}
    for item in items:
        category = str(item.get("category") or "other").strip().casefold()
        colour = str(item.get("colour") or "").strip().casefold()
        name = " ".join(str(item.get("name") or "").strip().casefold().split())
        # Colour alone is insufficient evidence that two garments are duplicates.
        key = (category, colour, name)
        groups.setdefault(key, []).append(item)
    duplicates = []
    for (category, colour, name), members in groups.items():
        if len(members) > 1:
            duplicates.append({
                "category": category, "colour": colour, "name": name,
                "item_ids": [member["id"] for member in members],
                "reason": "These items share the same manually entered name, category and colour; confirm whether they are actually duplicates.",
            })
    return {
        "possible_duplicates": duplicates,
        "item_count": len(items),
        "notice": "Possible duplicates are based on manually entered labels, not image comparison.",
    }


def capsule_plan(items, occasion="casual", climate="mild", max_items=12, *,
                 scan=None, preferred_colours=None, avoided_colours=None, preferred_style=None,
                 feedback=None):
    if not isinstance(max_items, int) or not 1 <= max_items <= 50:
        raise ValueError("max_items must be between 1 and 50")
    items = _items(items)
    priority = {"top": 0, "bottom": 1, "dress": 2, "shoes": 3, "outerwear": 4, "accessory": 5, "other": 6}
    # Select useful owned garments rather than alphabetical names. Full-outfit
    # compatibility is ranked using the same confirmed labels, scan and style
    # preferences as Discover, then balanced across garment categories.
    ranked_looks = plan_outfits(
        items, occasion, climate, limit=20, scan=scan,
        preferred_colours=preferred_colours,
        avoided_colours=avoided_colours,
        preferred_style=preferred_style, feedback=feedback)
    usefulness = Counter()
    for rank, look in enumerate(ranked_looks):
        for garment_id in look["item_ids"]:
            usefulness[garment_id] += max(1, 20 - rank)
    groups = {}
    for item in sorted(items, key=lambda x: (
            -usefulness[x["id"]], str(x.get("name") or "").casefold(), str(x["id"]))):
        groups.setdefault(item.get("category") or "other", []).append(item)
    # Take one from each relevant category first. The previous alphabetical
    # truncation could fill the entire capsule with tops, yielding no outfits.
    order = ["top", "bottom", "dress", "shoes"]
    if climate == "cold":
        order.append("outerwear")
    order += ["accessory", "other"]
    if climate != "cold":
        order.append("outerwear")
    chosen = []
    for category in order:
        if groups.get(category) and len(chosen) < max_items:
            chosen.append(groups[category].pop(0))
    remaining = sorted(
        [item for group in groups.values() for item in group],
        key=lambda x: (priority.get(x.get("category"), 6), str(x.get("name") or "").casefold()),
    )
    chosen.extend(remaining[:max(0, max_items - len(chosen))])
    counts = Counter(x.get("category") for x in chosen)
    missing = []
    if not counts["top"] and not counts["dress"]:
        missing.append("a versatile top or dress")
    if counts["top"] and not counts["bottom"]:
        missing.append("a versatile bottom")
    if not counts["shoes"]:
        missing.append("shoes suited to your occasion")
    if climate == "cold" and not counts["outerwear"]:
        missing.append("a layer for colder weather")
    return {
        "items": [{"id": x["id"], "name": x["name"], "category": x.get("category"), "colour": x.get("colour", "")} for x in chosen],
        "possible_outfits": plan_outfits(chosen, occasion, climate, limit=20, scan=scan,
                                        preferred_colours=preferred_colours,
                                        avoided_colours=avoided_colours,
                                        preferred_style=preferred_style, feedback=feedback),
        "missing_categories": missing,
        "wardrobe_insights": wardrobe_insights(items),
        "notice": "Capsule selection favours pieces used in your highest-ranked compatible owned outfits, then balances garment types. Rankings use confirmed garment details, not verified fit, stock or fabric.",
    }
