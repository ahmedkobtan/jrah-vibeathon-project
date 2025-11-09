"""
Provider-related API endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas import (
    PriceDetail,
    PriceEstimateItem,
    ProcedureSummary,
    ProviderSummary,
)
from app.services import NpiClient
from database import PriceTransparency, Procedure, Provider

_npi_client = NpiClient()

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


@router.get("/lookup", response_model=List[ProviderSummary])
def lookup_providers(
    city: str,
    state: str,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> List[ProviderSummary]:
    """
    Retrieve providers from the local database and supplement with NPI data.
    """
    normalized_state = state.upper()

    db_providers = (
        db.query(Provider)
        .filter(Provider.state == normalized_state)
        .filter(Provider.city.ilike(f"{city}%"))
        .order_by(Provider.name.asc())
        .limit(limit)
        .all()
    )

    summaries = [ProviderSummary.model_validate(provider) for provider in db_providers]
    if len(summaries) >= limit:
        return summaries

    seen_npis = {provider.npi for provider in db_providers if provider.npi}
    try:
        npi_results = _npi_client.lookup(city=city, state=normalized_state, limit=limit)
    except Exception as exc:  # pragma: no cover - external API failure
        raise HTTPException(status_code=502, detail=f"NPI lookup failed: {exc}") from exc

    for entry in npi_results:
        if entry.npi in seen_npis:
            continue

        summaries.append(
            ProviderSummary(
                id=None,
                npi=entry.npi,
                name=entry.name,
                address=entry.address.address_1,
                city=entry.address.city,
                state=entry.address.state,
                zip=entry.address.postal_code,
                phone=entry.address.telephone_number,
                latitude=None,
                longitude=None,
                website=None,
            )
        )

        if len(summaries) >= limit:
            break

    return summaries

