"""Isolated, opt-in supplier catalogue store. Never stores customer records."""
import os
import math
import re
from datetime import datetime, timezone

from services.catalogue_providers import get_provider

def live_supplier_readiness(provider_id: str) -> dict:
    """A staged XML/CSV snapshot must never be mistaken for live availability."""
    provider = get_provider(provider_id)
    if provider.kind != "wholesale":
        raise ValueError("Live supplier synchronisation is limited to approved wholesale providers")
    return {
        "provider_id": provider.id,
        "approved": False,
        "live_price_enabled": False,
        "live_stock_enabled": False,
        "order_routing_enabled": False,
        "requirements": [
            "Signed supplier agreement and permission to access a live catalogue",
            "Supplier-issued credentials configured in private server secrets",
            "Verified product, variant, currency, availability and tax mappings",
            "Supplier-specific rate limits, freshness window and safe retry policy",
            "Shipping eligibility for Australia and Moldova independently verified",
        ],
    }


COLLECTION_NAME = "supplier_catalogue_v2"
MAX_SCAN = 5000


def catalogue_enabled() -> bool:
    return os.environ.get("LUMIERE_SUPPLIER_CATALOGUE_ENABLED", "0") == "1"


async def read_catalogue(db, *, max_items=MAX_SCAN):
    """Read approved, active, normalised supplier records from the isolated collection."""
    if not catalogue_enabled():
        return []
    size = max(1, min(int(max_items), MAX_SCAN))
    records = await db[COLLECTION_NAME].find(
        {"active": True, "approved": True}, {"_id": 0}
    ).limit(size).to_list(length=size)
    safe = []
    for row in records:
        try:
            provider = get_provider(row["provider_id"])
            if provider.kind != "wholesale" or not row.get("source_verified"):
                continue
            if not row.get("external_id") or not row.get("name"):
                continue
            product = {k: v for k, v in row.items() if k not in (
                "active", "approved", "synced_at", "sync_batch")}
            # Snapshot does not imply current stock or live supplier API.
            product["live"] = True  # Existing ranking contract: source-backed product.
            safe.append(product)
        except (KeyError, ValueError):
            continue
    return safe


async def stage_catalogue(db, provider_id: str, products: list[dict], *,
                          approved: bool = False, activate: bool = False):
    """Upsert a small trusted batch; activation requires explicit independent approval.

    This does not delete or deactivate historical inventory. No customer tables
    are modified. Caller must run in a private authorised environment.
    """
    if not os.environ.get("LUMIERE_SUPPLIER_IMPORT_ENABLED") == "1":
        raise RuntimeError("Supplier import disabled")
    if activate and not approved:
        raise ValueError("Cannot activate supplier products without approval")
    provider = get_provider(provider_id)
    if provider.kind != "wholesale":
        raise ValueError("Only wholesale providers supported")
    if len(products) > 5000:
        raise ValueError("Batch too large")
    # Validate the entire batch before writing anything: a bad final row must
    # not leave the first rows partially staged.
    seen = set()
    for row in products:
        if not isinstance(row, dict) or row.get("provider_id") != provider_id or row.get("source_verified") is not True:
            raise ValueError("Unverified or mismatched catalogue product")
        identifier = row.get("external_id")
        name = row.get("name")
        if (not isinstance(identifier, str) or not identifier.strip() or
                len(identifier) > 150 or not isinstance(name, str) or
                not name.strip() or len(name) > 300):
            raise ValueError("Invalid supplier product identity")
        if identifier in seen:
            raise ValueError("Duplicate supplier product in batch")
        seen.add(identifier)
        # Price, currency and availability in imported snapshots are not verified live.
        currency = row.get("currency")
        if currency is not None and (not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency)):
            raise ValueError("Invalid supplier currency")
        price = row.get("price")
        if price is not None and (isinstance(price, bool) or not isinstance(price, (int, float)) or
                                  not math.isfinite(price) or price < 0):
            raise ValueError("Invalid supplier price")
        for field in ("sizes", "colour_names"):
            value = row.get(field)
            if value is not None and (not isinstance(value, list) or len(value) > 100 or
                any(not isinstance(v, str) or not v.strip() or len(v) > 100 for v in value)):
                raise ValueError("Invalid supplier variant values")
        if row.get("in_stock") is not None and not isinstance(row["in_stock"], bool):
            raise ValueError("Invalid supplier availability")
    await db[COLLECTION_NAME].create_index(
        [("provider_id", 1), ("external_id", 1)], unique=True)
    changed = 0
    for row in products:
        if row.get("provider_id") != provider_id or not row.get("source_verified"):
            raise ValueError("Unverified or mismatched catalogue product")
        key = {"provider_id": provider_id, "external_id": row["external_id"]}
        record = {k: v for k, v in row.items() if k != "_id"}
        record["synced_at"] = datetime.now(timezone.utc)
        # An ordinary staged refresh must not silently disable an already approved listing.
        # Approval state is created on first insertion; activation is a distinct
        # administrative decision, not implied by fetching or staging a feed.
        if approved and activate:
            record.update({"approved": True, "active": True})
        await db[COLLECTION_NAME].update_one(
            key,
            {"$set": record, "$setOnInsert": {
                "approved": False, "active": False,
            }},
            upsert=True,
        )
        changed += 1
    return changed
