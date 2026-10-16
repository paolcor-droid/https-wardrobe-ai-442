"""Isolated synthetic LUMIÈRE catalogue; NEVER supplier inventory or Try-On source.

Load only from an explicitly installed local XML file. No XML network fetching,
purchasing, synthetic reviews, or placeholder photo use.
"""
from functools import lru_cache
from pathlib import Path
import xml.etree.ElementTree as ET

DEMO_PATH = Path(__file__).resolve().parents[1] / "demo-data" / "demo_catalogue.xml"
LEGACY_DEMO_PATH = Path(__file__).resolve().parents[1] / ".lumiere-private-catalogue" / "demo_catalogue.xml"
MAX_BYTES = 64 * 1024 * 1024

# Catalogue values are Italian even when descriptions are in English.
# Normalize only demo presentation and matching, never alter the source XML.
COLOUR_EN = {
    "Nero": "Black", "Bianco": "White", "Panna": "Cream",
    "Grigio Perla": "Pearl Grey", "Grigio Melange": "Grey",
    "Antracite": "Charcoal", "Blu Navy": "Navy", "Azzurro": "Light Blue",
    "Denim Chiaro": "Light Blue", "Denim Medio": "Blue",
    "Denim Scuro": "Dark Blue", "Beige": "Beige", "Sabbia": "Sand",
    "Tortora": "Taupe", "Cammello": "Camel", "Cuoio": "Tan",
    "Marrone": "Brown", "Cioccolato": "Dark Brown",
    "Verde Oliva": "Olive", "Verde Salvia": "Sage Green",
    "Verde Bottiglia": "Forest Green", "Bordeaux": "Burgundy",
    "Rosso": "Red", "Terracotta": "Terracotta", "Corallo": "Coral",
    "Senape": "Mustard", "Blu Cobalto": "Cobalt Blue",
    "Rosa Cipria": "Blush Pink", "Lilla": "Lilac",
}
MATERIAL_EN = {
    "Cotone": "Cotton", "Lino": "Linen", "Lana": "Wool",
    "Lana Merino": "Merino Wool", "Cashmere": "Cashmere",
    "Seta": "Silk", "Viscosa": "Viscose", "Poliestere": "Polyester",
    "Poliammide": "Nylon", "Elastan": "Elastane",
    "Pelle Bovina": "Leather", "Pelle di Agnello": "Lambskin",
    "Camoscio": "Suede", "Paglia": "Straw", "Gomma": "Rubber",
}



@lru_cache(maxsize=2)
def _load(path: str, modified_ns: int) -> tuple[dict, ...]:
    source = Path(path)
    if source.stat().st_size > MAX_BYTES:
        raise ValueError("Demo catalogue exceeds the permitted size")
    root = ET.parse(source).getroot()
    if root.tag != "catalogue":
        raise ValueError("Expected a catalogue XML document")
    records = []
    for element in root.findall("products/product") or root.findall("product"):
        if element.get("active") == "false":
            continue
        sku = element.get("sku")
        if not sku:
            continue
        colours = element.findall("variants/colour")
        variants = [c for c in colours if any(int(s.get("stock", "0")) > 0
                    for s in c.findall("sizes/size"))]
        if not variants:
            continue
        original = element.findtext("price")
        try:
            price = float(original)
        except (ValueError, TypeError):
            continue
        sizes = list(dict.fromkeys(s.get("label", "") for c in variants
                          for s in c.findall("sizes/size") if int(s.get("stock", "0")) > 0))
        colour_names = list(dict.fromkeys(COLOUR_EN.get(c.get("name", ""), c.get("name", "")) for c in variants))
        materials = [f"{MATERIAL_EN.get(m.text or '', m.text or '')} {m.get('percentage', '')}%" for m in element.findall("composition/material") + element.findall("composition/part/material")]
        gender = element.findtext("gender", "")
        records.append({
            "provider_id": "lumiere-demo", "external_id": sku, "demo_xml_id": element.get("id", ""),
            "provider_kind": "demo", "source_verified": True, "live": True,
            "name": element.findtext("name", "") or "",
            "brand": element.findtext("brand", "") or "",
            "category": element.findtext("category", "") or "",
            "description": element.findtext("description", "") or "",
            "department": "mens" if gender == "Uomo" else "womens" if gender == "Donna" else "unisex",
            "price": price, "customer_price": price, "currency": "EUR",
            "colour_names": colour_names, "sizes": sizes, "materials": materials,
            "availability": 1, "image_url": None,
        })
    return tuple(records)


def demo_products(path: Path = DEMO_PATH) -> list[dict]:
    if path == DEMO_PATH and not path.is_file() and LEGACY_DEMO_PATH.is_file():
        path = LEGACY_DEMO_PATH
    if not path.is_file():
        return []
    return [dict(p) for p in _load(str(path), path.stat().st_mtime_ns)]


@lru_cache(maxsize=2)
def _outfits(path: str, modified_ns: int) -> tuple[dict, ...]:
    """Read coordinated outfit references from the bundled XML, not generated combinations."""
    root = ET.parse(path).getroot()
    outfits = []
    for el in root.findall("./outfits/outfit"):
        oid = el.get("id", "")
        if not oid:
            continue
        refs = []
        for item in el.iter("item"):
            for key in ("productId", "product_id", "sku", "ref"):
                if item.get(key):
                    refs.append(item.get(key))
                    break
        if len(refs) >= 2:
            outfits.append({"id": oid, "refs": refs})
    return tuple(outfits)


def demo_outfits(path: Path = DEMO_PATH) -> list[dict]:
    if path == DEMO_PATH and not path.is_file() and LEGACY_DEMO_PATH.is_file():
        path = LEGACY_DEMO_PATH
    if not path.is_file():
        return []
    return [dict(o) for o in _outfits(str(path), path.stat().st_mtime_ns)]
