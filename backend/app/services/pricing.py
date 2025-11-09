"""
Pricing service containing business logic for cost estimates.
"""

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import PriceTransparency, Procedure, Provider
from app.schemas import (
    PriceDetail,
    PriceEstimateItem,
    PriceEstimateResponse,
    PricingSummary,
    ProcedureSummary,
    ProviderSummary,
    QueryContext,
)


class PricingService:
    """
    Encapsulates pricing lookup logic.
    """

    def __init__(self, session: Session):
        self.session = session

    def fetch_price_estimates(
        self,
        *,
        cpt_code: str,
        payer_name: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        limit: int = 20,
    ) -> PriceEstimateResponse:
        """
        Fetch price transparency data filtered by the provided parameters.
        """
        query = (
            self.session.query(
                PriceTransparency,
                Provider,
                Procedure,
            )
            .join(Provider, PriceTransparency.provider_id == Provider.id)
            .join(Procedure, PriceTransparency.cpt_code == Procedure.cpt_code)
            .filter(PriceTransparency.cpt_code == cpt_code)
        )

        if payer_name:
            ilike_pattern = f"%{payer_name}%"
            query = query.filter(PriceTransparency.payer_name.ilike(ilike_pattern))

        if state:
            query = query.filter(Provider.state == state.upper())

        if zip_code:
            query = query.filter(Provider.zip == zip_code)

        records = (
            query.order_by(PriceTransparency.negotiated_rate.asc())
            .limit(limit)
            .all()
        )

        results = [
            PriceEstimateItem(
                provider=ProviderSummary.model_validate(provider),
                procedure=ProcedureSummary.model_validate(procedure),
                price=PriceDetail.model_validate(price),
            )
            for price, provider, procedure in records
        ]

        summary = self._calculate_summary(
            cpt_code=cpt_code,
            payer_name=payer_name,
            state=state,
            zip_code=zip_code,
        )

        summary.providers_count = len({item.provider.id for item in results})
        summary.payer_matches = len(results)

        return PriceEstimateResponse(
            query=QueryContext(
                cpt_code=cpt_code,
                payer_name=payer_name,
                state=state,
                zip=zip_code,
                limit=limit,
            ),
            summary=summary,
            results=results,
        )

    def _calculate_summary(
        self,
        *,
        cpt_code: str,
        payer_name: Optional[str],
        state: Optional[str],
        zip_code: Optional[str],
    ) -> PricingSummary:
        """
        Compute summary statistics for the given filters.
        """
        stats_query = self.session.query(
            func.min(PriceTransparency.negotiated_rate),
            func.max(PriceTransparency.negotiated_rate),
            func.avg(PriceTransparency.negotiated_rate),
        ).join(Provider, PriceTransparency.provider_id == Provider.id)

        stats_query = stats_query.filter(PriceTransparency.cpt_code == cpt_code)

        if payer_name:
            ilike_pattern = f"%{payer_name}%"
            stats_query = stats_query.filter(
                PriceTransparency.payer_name.ilike(ilike_pattern)
            )

        if state:
            stats_query = stats_query.filter(Provider.state == state.upper())

        if zip_code:
            stats_query = stats_query.filter(Provider.zip == zip_code)

        min_rate, max_rate, avg_rate = stats_query.one()

        return PricingSummary(
            providers_count=0,
            payer_matches=0,
            min_rate=float(min_rate) if min_rate is not None else None,
            max_rate=float(max_rate) if max_rate is not None else None,
            average_rate=float(avg_rate) if avg_rate is not None else None,
        )

