"""
Provider-related API endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas import PriceDetail, PriceEstimateItem, ProcedureSummary, ProviderSummary
from database import PriceTransparency, Procedure, Provider

router = APIRouter()


@router.get("/", response_model=List[ProviderSummary])
def list_providers(
    state: Optional[str] = None,
    city: Optional[str] = None,
    db: Session = Depends(get_db),
) -> List[ProviderSummary]:
    """
    Return all providers, optionally filtered by state or city.
    """
    query = db.query(Provider)

    if state:
        query = query.filter(Provider.state == state.upper())

    if city:
        query = query.filter(Provider.city.ilike(f"%{city}%"))

    providers = query.order_by(Provider.name.asc()).all()
    return [ProviderSummary.model_validate(provider) for provider in providers]


@router.get("/{provider_id}", response_model=ProviderSummary)
def get_provider(provider_id: int, db: Session = Depends(get_db)) -> ProviderSummary:
    """
    Retrieve a single provider by ID.
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    return ProviderSummary.model_validate(provider)


@router.get("/{provider_id}/prices", response_model=List[PriceEstimateItem])
def get_provider_prices(
    provider_id: int,
    db: Session = Depends(get_db),
) -> List[PriceEstimateItem]:
    """
    Retrieve all price transparency records for a provider.
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    records = (
        db.query(PriceTransparency, Procedure)
        .join(Procedure, PriceTransparency.cpt_code == Procedure.cpt_code)
        .filter(PriceTransparency.provider_id == provider_id)
        .order_by(PriceTransparency.payer_name.asc())
        .all()
    )

    provider_summary = ProviderSummary.model_validate(provider)
    return [
        PriceEstimateItem(
            provider=provider_summary,
            procedure=ProcedureSummary.model_validate(procedure),
            price=PriceDetail.model_validate(price),
        )
        for price, procedure in records
    ]

