"""Provider-neutral catalogue contracts for LUMIÈRE.

No retailer is scraped here. Live providers must return normalized, source-backed
products; demo or generated items must never be presented as live inventory.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional
from urllib.parse import urlparse


@dataclass(frozen=True)
class CatalogueProvider:
    id: str
    name: str
    kind: str
    home_url: str
    supports_live_catalogue: bool = False
    notes: Optional[str] = None

    def public_dict(self) -> dict:
        return asdict(self)


PROVIDERS = [
    CatalogueProvider("zara", "Zara", "retail", "https://www.zara.com/au/"),
    CatalogueProvider("hm", "H&M", "retail", "https://www2.hm.com/en_au/index.html"),
    CatalogueProvider("uniqlo", "UNIQLO", "retail", "https://www.uniqlo.com/au/en/"),
    CatalogueProvider("the-iconic", "THE ICONIC", "retail", "https://www.theiconic.com.au/"),
    CatalogueProvider("david-jones", "David Jones", "retail", "https://www.davidjones.com/"),
    CatalogueProvider("myer", "Myer", "retail", "https://www.myer.com.au/"),
    CatalogueProvider("asos", "ASOS", "retail", "https://www.asos.com/au/"),
    CatalogueProvider("country-road", "Country Road", "retail", "https://www.countryroad.com.au/"),
    CatalogueProvider("massimo-dutti", "Massimo Dutti", "retail", "https://www.massimodutti.com/au/"),
    CatalogueProvider(
        "romanelli-b2b", "Romanelli B2B", "wholesale",
        "https://www.romanellib2b.com/en/catalog",
        False,
        "Provider slot reserved for an authenticated catalogue/API integration; no live inventory is assumed.",
    ),
    CatalogueProvider("loro-piana", "Loro Piana", "retail", "https://www.loropiana.com/en-au/"),
    CatalogueProvider("armani", "Armani", "retail", "https://www.armani.com/en-au/"),
    CatalogueProvider(
        "matterhorn", "Matterhorn Wholesale", "wholesale",
        "https://matterhorn-wholesale.com/",
        False,
        "XML catalogue integration available for development; REST API remains disabled until authorised credentials are configured.",
    ),
    CatalogueProvider(
        "vaitto", "VAITTO", "wholesale", "https://vaitto.com/",
        False,
        "Pre-launch supplier enquiry pending; offline sample import only with authorised supplier data.",
    ),
    CatalogueProvider(
        "brandsdistribution", "Brandsdistribution", "wholesale",
        "https://www.brandsdistribution.com/",
        False,
        "Official catalogue/API integration candidate. Public sample exports are available; authenticated live API access is not enabled.",
    ),
]

_PROVIDER_BY_ID = {provider.id: provider for provider in PROVIDERS}


def list_providers() -> list[dict]:
    return [p.public_dict() for p in PROVIDERS]


def get_provider(provider_id: str) -> CatalogueProvider:
    provider = _PROVIDER_BY_ID.get(provider_id)
    if not provider:
        raise ValueError(f"Unknown catalogue provider: {provider_id}")
    return provider


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


_VALID_DEPARTMENTS = ("mens", "womens", "unisex")


def derive_department(category_path: str | None, category: str | None = None) -> str:
    """Derive mens/womens/unisex strictly from the genuine source taxonomy.

    Matterhorn category_path always leads with the department segment, e.g.
    "/MEN/..." or "/WOMEN/...". We read that genuine segment rather than guessing
    from loose substrings (so "WOMEN`S" is never misread as men's). Never inferred
    from images or the customer's selfie; unknown heads stay "unisex" so a gendered
    department is never fabricated.
    """
    text = " ".join([category_path or "", category or ""]).upper()
    if "UNISEX" in text:
        return "unisex"
    parts = [p.strip().upper() for p in (category_path or "").split("/") if p.strip()]
    head = parts[0] if parts else ""
    if head == "MEN":
        return "mens"
    if head.startswith("WOMEN") or head == "DRESSES":
        return "womens"
    return "unisex"


def _normalize_department(value: str | None) -> str:
    return value if value in _VALID_DEPARTMENTS else "unisex"


def normalize_product(provider_id: str, raw: dict) -> dict:
    """Normalize a verified provider record without inventing missing commerce data."""
    get_provider(provider_id)
    provider = get_provider(provider_id)
    required = ("external_id", "name")
    missing = [key for key in required if not raw.get(key)]
    if missing:
        raise ValueError(f"Missing source-backed product fields: {', '.join(missing)}")
    source_url = raw.get("source_url")
    if source_url and not _is_http_url(str(source_url)):
        raise ValueError("source_url must be an absolute http(s) URL when supplied")
    if provider.kind == "retail" and not source_url:
        raise ValueError("Retail catalogue products require a verified source_url")

    price = raw.get("price")
    if price is not None:
        try:
            price = float(price)
        except (TypeError, ValueError) as exc:
            raise ValueError("price must be numeric when supplied") from exc
        if price < 0:
            raise ValueError("price cannot be negative")

    return {
        "provider_id": provider_id,
        "provider_kind": provider.kind,
        "external_id": str(raw["external_id"]),
        "name": str(raw["name"]),
        "brand": raw.get("brand"),
        "category": raw.get("category"),
        "description": raw.get("description", ""),
        "price": price,
        "currency": raw.get("currency"),
        "image_url": raw.get("image_url"),
        "source_url": str(source_url) if source_url else None,
        "colour_names": raw.get("colour_names", []),
        "sizes": raw.get("sizes", []),
        "materials": raw.get("materials", []),
        "occasions": raw.get("occasions", []),
        "palette_tags": raw.get("palette_tags", []),
        "availability": raw.get("availability"),
        # Normalized shopping department (mens/womens/unisex). Explicit values
        # from source-backed records win; otherwise derived from the genuine
        # category taxonomy. Retail records without a department stay "unisex".
        "department": _normalize_department(
            raw.get("department") or derive_department(raw.get("category_path"), raw.get("category"))
        ),
        "source_verified": True,
        # Compatibility flag: this means a source-backed catalogue record, not
        # real-time inventory. live_inventory_enabled remains provider-specific.
        "live": True,
    }
