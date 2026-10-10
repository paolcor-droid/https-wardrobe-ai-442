from xml.etree import ElementTree as ET

from services.matterhorn_xml import map_product_element


SAMPLE = """<product id="231032">
<name>Push up model 231032 Róża</name>
<brand>Róża</brand>
<category_path>/WOMEN/Women's Lingerie/Bras/Push Up Bras</category_path>
<category id="1">Push Up Bras</category>
<color>white</color><type>Push up</type>
<images><image_url>https://matterhorn-wholesale.com/pics_source/1135449.jpg</image_url></images>
<price>20.9</price>
<description><![CDATA[Elegant bra. <div class='prod_data'><strong>Cotton</strong> 5 % <br><strong>Spandex</strong> 10 % <br><strong>Polyamide</strong> 85 %</div>]]></description>
<options>
<option id="M1295484"><option_name>70C</option_name><STOCK>3</STOCK><ean>5901306100041</ean></option>
<option id="M1295485"><option_name>70D</option_name><STOCK>2</STOCK><ean>5901306101017</ean></option>
</options></product>"""


def test_maps_real_matterhorn_shape():
    item = map_product_element(ET.fromstring(SAMPLE))
    assert item["external_id"] == "231032"
    assert item["brand"] == "Róża"
    assert item["colour_names"] == ["white"]
    assert item["price"] == 20.9
    assert item["currency"] == "AUD"
    assert item["sizes"] == ["70C", "70D"]
    assert item["availability"] == "5"
    assert item["materials"] == ["Cotton 5%", "Spandex 10%", "Polyamide 85%"]
    assert item["_matterhorn"]["variants"][0]["stock"] == 3


def test_rejects_missing_source_identity():
    product = ET.fromstring("<product><name>Test</name></product>")
    try:
        map_product_element(product)
    except ValueError as exc:
        assert "missing id or name" in str(exc)
    else:
        raise AssertionError("Expected missing Matterhorn id to be rejected")
