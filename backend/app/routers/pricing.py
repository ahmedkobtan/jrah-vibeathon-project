"""
Pricing endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_search_client
from app.schemas import PriceEstimateResponse
from app.services import PricingService

router = APIRouter()


@router.get(
    "/estimates",
    response_model=PriceEstimateResponse,
    summary="Get price transparency data for a CPT code",
)
def get_price_estimates(
    cpt_code: str = Query(..., description="CPT code to look up"),
    payer_name: Optional[str] = Query(
        None,
        description="Filter by payer/insurance carrier name (case-insensitive, partial match)",
    ),
    state: Optional[str] = Query(
        None, description="Filter by two-letter state abbreviation"
    ),
    zip_code: Optional[str] = Query(
        None, description="Filter by provider ZIP code (exact match)"
    ),
    provider_city: Optional[str] = Query(
        None, description="Optional provider city filter / fallback"
    ),
    provider_state: Optional[str] = Query(
        None, description="Provider state used for fallback lookups"
    ),
    provider_limit: int = Query(
        20,
        ge=1,
        le=50,
        description="Maximum number of providers to pull when falling back to NPI data",
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of price records to return",
    ),
    db: Session = Depends(get_db),
    search_client = Depends(get_search_client),
) -> PriceEstimateResponse:
    """
    Return pricing details for the requested CPT code.
    
    Pricing lookup follows this waterfall strategy:
    1. Database: Look for actual negotiated rates from price transparency data
    2. NPI Registry: If no data, find providers via CMS NPI Registry and estimate prices
    3. Web Search: If NPI yields no results, search web for pricing (DuckDuckGo preferred, Google if configured)
    4. Algorithmic: Generate reasonable estimates based on Medicare rates
    """
    service = PricingService(db, search_client=search_client)
    return service.fetch_price_estimates(
        cpt_code=cpt_code,
        payer_name=payer_name,
        state=state,
        zip_code=zip_code,
        limit=limit,
        provider_city=provider_city,
        provider_state=provider_state,
        provider_limit=provider_limit,
    )

