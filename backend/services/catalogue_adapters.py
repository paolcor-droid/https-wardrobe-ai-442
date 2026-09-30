"""Contracts for authorised catalogue adapters.

Adapters are intentionally retrieval-only: they translate a provider's real,
source-backed records into LUMIÈRE's normalised product contract. Personalisation
and ranking happen later in product_recommendations.py.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from services.catalogue_providers import get_provider, normalize_product


class CatalogueAdapter(ABC):
    provider_id: str

    def __init__(self) -> None:
        provider = get_provider(self.provider_id)
        if not provider.supports_live_catalogue:
            raise RuntimeError(
                f"{provider.name} is not enabled for live catalogue retrieval. "
                "Authorised access must be configured first."
            )

    @abstractmethod
    async def fetch_products(self, query: dict | None = None) -> Iterable[dict]:
        """Return source-backed provider records. Never return generated products."""
        raise NotImplementedError

    async def normalized_products(self, query: dict | None = None) -> list[dict]:
        records = await self.fetch_products(query)
        return [normalize_product(self.provider_id, record) for record in records]


def enabled_live_provider_ids() -> list[str]:
    """Expose only providers explicitly marked as having authorised live access."""
    from services.catalogue_providers import PROVIDERS

    return [provider.id for provider in PROVIDERS if provider.supports_live_catalogue]
