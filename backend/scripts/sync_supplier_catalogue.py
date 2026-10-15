"""Manually stage an authorised private supplier snapshot into isolated Mongo.

Never calls supplier APIs, writes customer collections or activates products.
Requires LUMIERE_SUPPLIER_IMPORT_ENABLED=1, MONGO_URL, DB_NAME.
Usage:
 python scripts/sync_supplier_catalogue.py --provider vaitto --snapshot /private/vaitto.json
Use a private scheduler only after provider licences and credentials are approved.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from services.supplier_catalogue_store import stage_catalogue


async def sync(provider: str, source: Path):
    if os.getenv("LUMIERE_SUPPLIER_IMPORT_ENABLED") != "1":
        raise RuntimeError("Supplier sync is disabled; set explicit import gate")
    if source.stat().st_size > 100 * 1024 * 1024:
        raise ValueError("Supplier snapshot exceeds size limit")
    records = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Snapshot must be a JSON array")
    client = AsyncIOMotorClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=5000)
    try:
        db = client[os.environ["DB_NAME"]]
        total = 0
        for offset in range(0, len(records), 5000):
            total += await stage_catalogue(db, provider, records[offset:offset + 5000],
                                           approved=False, activate=False)
        print(json.dumps({"staged": total, "provider": provider,
                          "active": False, "approved": False}))
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--snapshot", required=True, type=Path)
    args = parser.parse_args()
    asyncio.run(sync(args.provider, args.snapshot))
