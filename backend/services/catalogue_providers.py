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


def normalize_product(provider_id: str, raw: dict) -> dict:
    """Normalize a verified provider record without inventing missing commerce data."""
    get_provider(provider_id)
    required = ("external_id", "name", "source_url")
    missing = [key for key in required if not raw.get(key)]
    if missing:
        raise ValueError(f"Missing source-backed product fields: {', '.join(missing)}")
    if not _is_http_url(str(raw["source_url"])):
        raise ValueError("source_url must be an absolute http(s) URL")

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
        "external_id": str(raw["external_id"]),
        "name": str(raw["name"]),
        "brand": raw.get("brand"),
        "category": raw.get("category"),
        "description": raw.get("description", ""),
        "price": price,
        "currency": raw.get("currency"),
        "image_url": raw.get("image_url"),
        "source_url": str(raw["source_url"]),
        "colour_names": raw.get("colour_names", []),
        "sizes": raw.get("sizes", []),
        "materials": raw.get("materials", []),
        "occasions": raw.get("occasions", []),
        "palette_tags": raw.get("palette_tags", []),
        "availability": raw.get("availability"),
        "live": True,
    }
