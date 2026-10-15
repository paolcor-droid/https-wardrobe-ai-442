"""Offline supplier imports use only test files; never touch customer data."""
import csv
import json
import pytest
from scripts.import_supplier_catalogue import import_feed


def test_import_authorised_csv_without_overwriting(tmp_path):
    source = tmp_path / "supplier.csv"
    with source.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["sku", "title", "cost", "shade", "sizes"])
        writer.writeheader()
        writer.writerow({"sku": "SKU1", "title": "Linen shirt", "cost": "35",
                         "shade": "Navy|Cream", "sizes": "S|M"})
        writer.writerow({"sku": "SKU1", "title": "Duplicated shirt", "cost": "35",
                         "shade": "Navy", "sizes": "S"})
    dest = tmp_path / "private" / "snapshot.json"
    mapping = {"external_id": "sku", "name": "title", "price": "cost",
               "colour_names": "shade", "sizes": "sizes"}
    report = import_feed("vaitto", source, mapping, dest)
    assert report["imported"] == 1
    assert report["skipped"] == 1
    product = json.loads(dest.read_text())[0]
    assert product["provider_id"] == "vaitto"
    assert product["colour_names"] == ["Navy", "Cream"]
    assert product["sizes"] == ["S", "M"]
    assert product["source_verified"] is True
    with pytest.raises(FileExistsError):
        import_feed("vaitto", source, mapping, dest)


def test_invalid_source_keeps_export_absent(tmp_path):
    source = tmp_path / "empty.json"
    source.write_text(json.dumps([{"bad": "not a product"}]))
    target = tmp_path / "missing.json"
    with pytest.raises(ValueError, match="No valid"):
        import_feed("brandsdistribution", source,
                    {"external_id": "sku", "name": "title"}, target)
    assert not target.exists()


def test_unapproved_provider_rejected(tmp_path):
    source = tmp_path / "feed.json"
    source.write_text("[]")
    with pytest.raises(ValueError, match="not approved"):
        import_feed("zara", source, {"external_id": "sku", "name": "title"}, tmp_path / "out.json")
