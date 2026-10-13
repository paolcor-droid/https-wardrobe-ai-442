"""Discover and Try-On must resolve products against one catalogue source."""
from pathlib import Path


def test_discover_and_private_tryon_share_imported_catalogue():
    code = (Path(__file__).resolve().parents[1] / "server.py").read_text()
    assert "def load_customer_catalogue():" in code
    discover = code.split("async def recommend_catalogue_for_customer", 1)[1].split("async def ", 1)[0]
    prepare = code.split("async def prepare_trusted_garment_for_customer", 1)[1].split("async def ", 1)[0]
    assert "raw_products, source = load_customer_catalogue()" in discover
    assert "products, _ = load_customer_catalogue()" in prepare
    assert 'str(product.get("external_id", "")) == product_id' in prepare
