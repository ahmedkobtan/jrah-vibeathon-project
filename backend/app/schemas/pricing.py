"""
Pricing-related response models.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from .procedure import ProcedureSummary
from .provider import ProviderSummary


class PriceDetail(BaseModel):
    """
    Detailed pricing information for a single provider/payer combination.
    """

    id: Optional[int] = None
    payer_name: Optional[str] = None
    negotiated_rate: Optional[float] = None
    min_negotiated_rate: Optional[float] = None
    max_negotiated_rate: Optional[float] = None
    standard_charge: Optional[float] = None
    cash_price: Optional[float] = None
    in_network: Optional[bool] = None
    data_source: Optional[str] = None
    confidence_score: Optional[float] = None
    last_updated: Optional[date] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PriceEstimateItem(BaseModel):
    """
    Combines provider, procedure, and price detail into a single result row.
    """

    provider: ProviderSummary
    procedure: ProcedureSummary
    price: PriceDetail


class PricingSummary(BaseModel):
    """
    Summary statistics for a pricing query.
    """

    providers_count: int
    payer_matches: int
    min_rate: Optional[float] = None
    max_rate: Optional[float] = None
    average_rate: Optional[float] = None


class QueryContext(BaseModel):
    """
    Echoes the query parameters back to the client.
    """

    cpt_code: str
    payer_name: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    limit: int


class PriceEstimateResponse(BaseModel):
    """
    Response payload for the pricing estimates endpoint.
    """

    query: QueryContext
    summary: PricingSummary
    results: list[PriceEstimateItem]

