"""Isolated synthetic LUMIÈRE catalogue; NEVER supplier inventory or Try-On source.

Load only from an explicitly installed local XML file. No XML network fetching,
purchasing, synthetic reviews, or placeholder photo use.
"""
from functools import lru_cache
from pathlib import Path
import xml.etree.ElementTree as ET

DEMO_PATH = Path(__file__).resolve().parents[1] / ".lumiere-private-catalogue" / "demo_catalogue.xml"
MAX_BYTES = 64 * 1024 * 1024


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
        colour_names = list(dict.fromkeys(c.get("name", "") for c in variants))
        materials = [f"{m.text or ''} {m.get('percentage', '')}%" for m in element.findall("composition/material") + element.findall("composition/part/material")]
        gender = element.findtext("gender", "")
        records.append({
            "provider_id": "lumiere-demo", "external_id": sku,
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
    if not path.is_file():
        return []
    return [dict(p) for p in _load(str(path), path.stat().st_mtime_ns)]
