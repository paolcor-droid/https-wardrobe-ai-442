"""Pure Discover filtering, stable IDs and safe presentation metadata.

Apply eligibility/ranking before pagination; never weaken palette or avoided-colour rules.
"""
import hashlib
import re


def product_key(product):
    provider = str(product.get("provider_id") or "")
    external = str(product.get("external_id") or "")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", provider) or not external:
        raise ValueError("Missing or invalid provider product identity")
    return provider + ":" + hashlib.sha256(external.encode("utf-8")).hexdigest()[:24]


def matches(product, filters):
    def contains(field, value):
        return not value or value.casefold() in str(product.get(field) or "").casefold()
    query = (filters.get("q") or "").strip().casefold()
    if query and not all(term in " ".join(str(product.get(k) or "") for k in
        ("name", "brand", "category", "description")).casefold()
        for term in query.split()):
        return False
    if not contains("brand", filters.get("brand")):
        return False
    if not contains("category", filters.get("category")):
        return False
    colour = (filters.get("colour") or "").casefold()
    if colour and not any(colour in str(c).casefold() for c in product.get("colour_names") or []):
        return False
    size = (filters.get("size") or "").casefold()
    if size and not any(size == str(s).casefold() for s in product.get("sizes") or []):
        return False
    price = product.get("customer_price", product.get("price"))
    if filters.get("min_price") is not None and (price is None or price < filters["min_price"]):
        return False
    if filters.get("max_price") is not None and (price is None or price > filters["max_price"]):
        return False
    return True


def paginate(ranked, filters, page=1, per_page=20):
    if page < 1 or page > 500 or per_page < 1 or per_page > 60:
        raise ValueError("Invalid pagination")
    selected = [p for p in ranked if matches(p, filters)]
    start = (page - 1) * per_page
    return selected[start:start + per_page], len(selected)


def catalogue_view(product, customer_view):
    record = customer_view(product)
    record["product_id"] = product_key(product)
    record["tryon_supported"] = product.get("provider_id") == "matterhorn"
    record["price_status"] = "supplier_snapshot"
    record["stock_status"] = "unverified_snapshot"
    return record
