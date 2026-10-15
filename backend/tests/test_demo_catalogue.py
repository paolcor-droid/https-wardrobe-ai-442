"""Demonstration XML is never treated as real supplier inventory."""
from services.demo_catalogue import demo_products


XML = """<?xml version="1.0" encoding="UTF-8"?>
<catalogue><product id="1" sku="WTOP-00001" active="true">
<name>Blusa in Lino</name><brand>Illustrative Label</brand>
<gender>Donna</gender><category>Tops</category><description>Sample</description>
<price currency="EUR">45.90</price>
<composition><material percentage="100">Lino</material></composition>
<variants><colour name="Blu Navy" hex="#1B2A49">
<sizes><size label="M" stock="3"/><size label="L" stock="0"/></sizes></colour>
<colour name="Rosso"><sizes><size label="M" stock="0"/></sizes></colour></variants>
</product><product id="2" sku="MTOP-00002" active="false"><name>Hidden</name></product>
</catalogue>"""


def test_demo_xml_loader_is_read_only_and_disables_image_and_sales(tmp_path):
    path = tmp_path / "demo.xml"
    path.write_text(XML, encoding="utf-8")
    products = demo_products(path)
    assert len(products) == 1
    item = products[0]
    assert item["external_id"] == "WTOP-00001"
    assert item["provider_id"] == "lumiere-demo"
    assert item["provider_kind"] == "demo"
    assert item["department"] == "womens"
    assert item["currency"] == "EUR"
    assert item["image_url"] is None
    assert item["sizes"] == ["M"]
    assert item["colour_names"] == ["Blu Navy"]
    assert demo_products(path) == products


def test_missing_demo_xml_keeps_supplier_catalogue_unaffected(tmp_path):
    assert demo_products(tmp_path / "not-here.xml") == []
