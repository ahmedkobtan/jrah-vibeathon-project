"""
Client for the CMS NPI Registry API.
"""

from __future__ import annotations

from typing import List, Optional

import httpx
from pydantic import BaseModel, Field


class NpiAddress(BaseModel):
    """Normalized address information returned by the NPI Registry API."""

    address_1: str = Field(default="")
    address_2: Optional[str] = None
    city: str = Field(default="")
    state: str = Field(default="")
    postal_code: str = Field(default="")
    telephone_number: Optional[str] = None
    fax_number: Optional[str] = None


class NpiProvider(BaseModel):
    """Minimal provider representation used by the application."""

    npi: str
    name: str
    address: NpiAddress
    taxonomy_code: Optional[str] = None
    taxonomy_description: Optional[str] = None


class NpiClient:
    """
    Thin wrapper around the CMS NPI Registry REST API.
    """

    BASE_URL = "https://npiregistry.cms.hhs.gov/api/"

    def __init__(self, *, timeout: float = 5.0):
        self._client = httpx.Client(timeout=timeout)

    def lookup(
        self,
        *,
        city: str,
        state: str,
        limit: int = 20,
    ) -> List[NpiProvider]:
        """
        Fetch providers for a given city/state combination.

        Only organization records (NPI-2) are returned.
        """
        params = {
            "version": "2.1",
            "city": city,
            "state": state,
            "limit": min(limit, 200),
        }

        response = self._client.get(self.BASE_URL, params=params)
        response.raise_for_status()
        payload = response.json()

        providers: List[NpiProvider] = []

        for entry in payload.get("results", []):
            if entry.get("enumeration_type") != "NPI-2":
                continue

            org_name = entry.get("basic", {}).get("organization_name")
            if not org_name:
                continue

            location = next(
                (
                    address
                    for address in entry.get("addresses", [])
                    if address.get("address_purpose") == "LOCATION"
                ),
                None,
            )

            if not location:
                continue

            taxonomy = next(
                (tax for tax in entry.get("taxonomies", []) if tax.get("primary")),
                None,
            )

            providers.append(
                NpiProvider(
                    npi=entry.get("number", ""),
                    name=org_name,
                    address=NpiAddress(
                        address_1=location.get("address_1", ""),
                        address_2=location.get("address_2"),
                        city=location.get("city", ""),
                        state=location.get("state", ""),
                        postal_code=location.get("postal_code", ""),
                        telephone_number=location.get("telephone_number"),
                        fax_number=location.get("fax_number"),
                    ),
                    taxonomy_code=taxonomy.get("code") if taxonomy else None,
                    taxonomy_description=taxonomy.get("desc") if taxonomy else None,
                )
            )

        return providers

