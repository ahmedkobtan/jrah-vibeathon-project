from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Protocol


@dataclass
class ProviderCandidate:
    provider_id: str
    name: str
    state: str
    distance_miles: Optional[float]


@dataclass
class PriceQuote:
    provider_id: str
    cpt_code: str
    rate: float
    source: str
    confidence: float


class ProviderRepository(Protocol):
    async def search(
        self,
        *,
        zip: str,
        radius: int,
        include_out_of_network: bool,
    ) -> Iterable[ProviderCandidate]:
        ...


class PricingRepository(Protocol):
    async def quotes_for(
        self, *, provider_ids: Iterable[str], cpt_code: str, insurance: str
    ) -> Iterable[PriceQuote]:
        ...
