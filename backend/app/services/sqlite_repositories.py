from __future__ import annotations

import asyncio
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .types import PriceQuote, ProviderCandidate, PricingRepository, ProviderRepository

ZIP_COORDS: dict[str, Tuple[float, float]] = {
    "64801": (37.0842, -94.5133),
    "64804": (37.0473, -94.5115),
    "72758": (36.3064, -94.1600),
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in miles between two lat/lon pairs."""

    radius = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


@dataclass
class SQLiteConfig:
    db_path: Path


class SQLiteProviderRepository(ProviderRepository):
    def __init__(self, config: SQLiteConfig) -> None:
        self._config = config

    async def search(
        self,
        *,
        zip: str,
        radius: int,
        include_out_of_network: bool,
    ) -> Iterable[ProviderCandidate]:
        _ = include_out_of_network  # demo ignores network filtering for now
        return await asyncio.to_thread(self._query_providers, zip, radius)

    def _query_providers(self, zip_code: str, radius: int) -> List[ProviderCandidate]:
        with sqlite3.connect(self._config.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT provider_id, name, state, lat, lon FROM providers"
            )
            rows = cursor.fetchall()

        user_coords: Optional[Tuple[float, float]] = ZIP_COORDS.get(zip_code)
        providers: List[ProviderCandidate] = []
        for provider_id, name, state, lat, lon in rows:
            distance: Optional[float] = None
            if user_coords and lat is not None and lon is not None:
                distance = haversine_distance(user_coords[0], user_coords[1], lat, lon)
                if distance > radius:
                    continue
            providers.append(ProviderCandidate(provider_id, name, state, distance))
        return providers


class SQLitePricingRepository(PricingRepository):
    def __init__(self, config: SQLiteConfig) -> None:
        self._config = config

    async def quotes_for(
        self, *, provider_ids: Iterable[str], cpt_code: str, insurance: str
    ) -> Iterable[PriceQuote]:
        return await asyncio.to_thread(self._query_quotes, provider_ids, cpt_code, insurance)

    def _query_quotes(
        self, provider_ids: Iterable[str], cpt_code: str, insurance: str
    ) -> List[PriceQuote]:
        provider_ids_list = list(provider_ids)
        if not provider_ids_list:
            return []
        placeholders = ",".join(["?"] * len(provider_ids_list))
        params = provider_ids_list + [cpt_code, insurance]
        sql = (
            "SELECT provider_id, cpt_code, negotiated_rate, source, confidence "
            "FROM price_transparency WHERE provider_id IN ("
            f"{placeholders}) AND cpt_code = ? AND payer_name = ?"
        )
        with sqlite3.connect(self._config.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return [
            PriceQuote(provider_id, cpt, rate, source or "", confidence or 0.0)
            for provider_id, cpt, rate, source, confidence in rows
        ]
