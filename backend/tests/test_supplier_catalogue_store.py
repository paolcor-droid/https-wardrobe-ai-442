"""Synthetic isolated tests for staged supplier catalogues; no real Mongo connection."""
import pytest
import asyncio
from services import supplier_catalogue_store as store


class Cursor:
    def __init__(self, rows):
        self.rows = rows
    def limit(self, n):
        self.rows = self.rows[:n]
        return self
    async def to_list(self, length):
        return self.rows[:length]


class SupplierCollection:
    def __init__(self):
        self.rows = {}
    async def create_index(self, keys, unique=False):
        assert unique is True
    async def update_one(self, key, update, upsert=False):
        assert upsert
        identity = (key["provider_id"], key["external_id"])
        existing = self.rows.get(identity, dict(update.get("$setOnInsert", {})))
        existing.update(update["$set"])
        self.rows[identity] = existing
    def find(self, query, projection):
        return Cursor([dict(row) for row in self.rows.values()
                       if row.get("active") == query["active"] and
                       row.get("approved") == query["approved"]])


class DB:
    def __init__(self):
        self.catalogue = SupplierCollection()
    def __getitem__(self, key):
        assert key == "supplier_catalogue_v2"
        return self.catalogue


def product(provider="vaitto", identifier="sku-1"):
    return {"provider_id": provider, "provider_kind": "wholesale",
            "external_id": identifier, "name": "Cotton shirt",
            "source_verified": True, "live": True, "price": 20, "currency": "AUD"}


def test_disabled_import_and_disabled_discover(monkeypatch):
    async def run():
        monkeypatch.delenv("LUMIERE_SUPPLIER_IMPORT_ENABLED", raising=False)
        monkeypatch.delenv("LUMIERE_SUPPLIER_CATALOGUE_ENABLED", raising=False)
        db = DB()
        with pytest.raises(RuntimeError, match="disabled"):
            await store.stage_catalogue(db, "vaitto", [product()])
        assert await store.read_catalogue(db) == []
    asyncio.run(run())

def test_staging_cannot_activate_without_approval(monkeypatch):
    async def run():
        monkeypatch.setenv("LUMIERE_SUPPLIER_IMPORT_ENABLED", "1")
        monkeypatch.setenv("LUMIERE_SUPPLIER_CATALOGUE_ENABLED", "1")
        db = DB()
        with pytest.raises(ValueError, match="approval"):
            await store.stage_catalogue(db, "vaitto", [product()], activate=True)
        assert await store.stage_catalogue(db, "vaitto", [product()]) == 1
        assert await store.read_catalogue(db) == []
        await store.stage_catalogue(db, "vaitto", [product()], approved=True, activate=True)
        result = await store.read_catalogue(db)
        assert len(result) == 1 and result[0]["external_id"] == "sku-1"
        assert "synced_at" not in result[0]
    asyncio.run(run())

def test_provider_mismatch_rejected(monkeypatch):
    async def run():
        monkeypatch.setenv("LUMIERE_SUPPLIER_IMPORT_ENABLED", "1")
        with pytest.raises(ValueError, match="mismatched"):
            await store.stage_catalogue(DB(), "vaitto", [product(provider="matterhorn")])
    asyncio.run(run())



@pytest.mark.parametrize("invalid", [
    [product(), product()],
    [product(), product(identifier="")],
    [product(), product(provider="matterhorn", identifier="sku-2")],
    [product(), {**product(identifier="sku-2"), "source_verified": "yes"}],
    [product(), {**product(identifier="sku-2"), "name": " "}],
])
def test_invalid_batch_never_partially_writes(monkeypatch, invalid):
    """Preflight every supplier row before the first database write."""
    async def run():
        monkeypatch.setenv("LUMIERE_SUPPLIER_IMPORT_ENABLED", "1")
        db = DB()
        with pytest.raises(ValueError):
            await store.stage_catalogue(db, "vaitto", invalid)
        assert db.catalogue.rows == {}
    asyncio.run(run())


def test_valid_distinct_supplier_products_stage_without_activation(monkeypatch):
    async def run():
        monkeypatch.setenv("LUMIERE_SUPPLIER_IMPORT_ENABLED", "1")
        monkeypatch.setenv("LUMIERE_SUPPLIER_CATALOGUE_ENABLED", "1")
        db = DB()
        assert await store.stage_catalogue(db, "vaitto", [
            product(identifier="sku-1"), product(identifier="sku-2"),
        ]) == 2
        assert len(db.catalogue.rows) == 2
        assert await store.read_catalogue(db) == []
    asyncio.run(run())
