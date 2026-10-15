"""Synthetic isolated tests for staged supplier catalogues; no real Mongo connection."""
import pytest
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
        self.rows[(key["provider_id"], key["external_id"])] = update["$set"]
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


@pytest.mark.asyncio
async def test_disabled_import_and_disabled_discover(monkeypatch):
    monkeypatch.delenv("LUMIERE_SUPPLIER_IMPORT_ENABLED", raising=False)
    monkeypatch.delenv("LUMIERE_SUPPLIER_CATALOGUE_ENABLED", raising=False)
    db = DB()
    with pytest.raises(RuntimeError, match="disabled"):
        await store.stage_catalogue(db, "vaitto", [product()])
    assert await store.read_catalogue(db) == []


@pytest.mark.asyncio
async def test_staging_cannot_activate_without_approval(monkeypatch):
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


@pytest.mark.asyncio
async def test_provider_mismatch_rejected(monkeypatch):
    monkeypatch.setenv("LUMIERE_SUPPLIER_IMPORT_ENABLED", "1")
    with pytest.raises(ValueError, match="mismatched"):
        await store.stage_catalogue(DB(), "vaitto", [product(provider="matterhorn")])
