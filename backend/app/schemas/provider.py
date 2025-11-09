"""
Provider response models.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProviderSummary(BaseModel):
    """
    Summary information about a provider suitable for API responses.
    """

    id: Optional[int] = None
    name: str
    npi: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    website: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

