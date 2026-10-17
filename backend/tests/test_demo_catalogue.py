"""Demonstration XML is never treated as real supplier inventory."""
from services.demo_catalogue import demo_products, demo_outfits, english_name


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
    assert item["colour_names"] == ["Navy"]
    assert demo_products(path) == products


def test_missing_demo_xml_keeps_supplier_catalogue_unaffected(tmp_path):
    assert demo_products(tmp_path / "not-here.xml") == []


def test_ten_thousand_product_schema_with_nested_product_and_composition_parts(tmp_path):
    xml = """<catalogue totalProducts="10000" totalOutfits="3000"><products>
    <product id="1" sku="MFOO-00001" active="true">
    <name>Sneakers in Tela</name><brand>Example Test</brand>
    <gender>Uomo</gender><category>Footwear</category>
    <description lang="it">Demo footwear</description><price currency="EUR">74.90</price>
    <composition><part name="Tomaia"><material percentage="100">Cotone</material></part>
    <part name="Suola"><material percentage="100">Gomma</material></part></composition>
    <variants><colour name="Blu Navy"><sizes>
    <size label="39" stock="0"/><size label="40" stock="7"/>
    </sizes></colour></variants></product></products>
    <outfits><outfit id="OUT-00001"><items><item productId="1"/></items></outfit></outfits>
    </catalogue>"""
    path = tmp_path / "tenk.xml"
    path.write_text(xml, encoding="utf-8")
    products = demo_products(path)
    assert len(products) == 1
    assert products[0]["materials"] == ["Cotton 100%", "Rubber 100%"]
    assert products[0]["sizes"] == ["40"]
    assert products[0]["image_url"] is None


def test_outfits_keep_actual_xml_references(tmp_path):
    path = tmp_path / "outfits.xml"
    path.write_text('''<catalogue><products>
      <product id="2" sku="M-2" active="true"><name>Shirt</name><gender>Uomo</gender>
        <price>20</price><variants><colour name="Blu Navy"><sizes><size label="M" stock="1"/></sizes></colour></variants></product>
      <product id="7" sku="M-7" active="true"><name>Trousers</name><gender>Uomo</gender>
        <price>40</price><variants><colour name="Nero"><sizes><size label="M" stock="1"/></sizes></colour></variants></product>
    </products><outfits><outfit id="OUT-1"><items><item productId="2"/><item productId="7"/></items></outfit></outfits></catalogue>''')
    products = demo_products(path)
    assert [p["demo_xml_id"] for p in products] == ["2", "7"]
    assert demo_outfits(path) == [{"id": "OUT-1", "refs": ["2", "7"], "colours": ["", ""], "season": "", "occasion": "", "style": "", "source_season": "", "source_occasion": "", "source_style": ""}]


def test_demo_product_names_translate_without_mutating_identity():
    assert english_name("T-shirt Girocollo") == "Crew-neck T-shirt"
    assert english_name("Pantaloni Chino") == "Chino trousers"
    assert english_name("Giacca Sfoderata") == "Unlined jacket"


def test_outfit_metadata_translation_keeps_original_xml(tmp_path):
    from services.demo_catalogue import translate_outfit_label
    assert translate_outfit_label("Estate", "season") == "Summer"
    assert translate_outfit_label("Lavoro", "occasion") == "Work"
    assert translate_outfit_label("Classico", "style") == "Classic"
    path = tmp_path / "translated.xml"
    path.write_text('<catalogue><outfits><outfit id="OUT-X" season="Estate" occasion="Lavoro" style="Classico"><items><item productId="1"/><item productId="2"/></items></outfit></outfits></catalogue>')
    record = demo_outfits(path)[0]
    assert (record["season"], record["occasion"], record["style"]) == ("Summer", "Work", "Classic")
    assert (record["source_season"], record["source_occasion"], record["source_style"]) == ("Estate", "Lavoro", "Classico")
