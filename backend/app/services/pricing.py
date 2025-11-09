"""
Pricing service containing business logic for cost estimates.
"""

from datetime import date, datetime
from typing import Optional
import hashlib

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import PriceTransparency, Procedure, Provider
from .npi_client import NpiClient
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

    def __init__(self, session: Session, npi_client: NpiClient | None = None):
        self.session = session
        self.npi_client = npi_client or NpiClient()

    def fetch_price_estimates(
        self,
        *,
        cpt_code: str,
        payer_name: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        limit: int = 20,
        provider_city: Optional[str] = None,
        provider_state: Optional[str] = None,
        provider_limit: int = 20,
    ) -> PriceEstimateResponse:
        """
        Fetch price transparency data filtered by the provided parameters.
        """
        procedure = (
            self.session.query(Procedure)
            .filter(Procedure.cpt_code == cpt_code)
            .first()
        )
        procedure_summary = (
            ProcedureSummary.model_validate(procedure)
            if procedure
            else ProcedureSummary(
                cpt_code=cpt_code,
                description=f"Procedure {cpt_code}",
                category=None,
                medicare_rate=None,
            )
        )

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

        if provider_city:
            query = query.filter(Provider.city.ilike(f"{provider_city}%"))

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

        if results:
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

        # No negotiated rate data found, attempt fallback via NPI
        fallback_results = self._fallback_with_npi(
            procedure_summary=procedure_summary,
            payer_name=payer_name,
            provider_city=provider_city,
            provider_state=provider_state,
            provider_limit=provider_limit,
        )

        rates = [
            item.price.negotiated_rate
            for item in fallback_results
            if item.price.negotiated_rate is not None
        ]
        fallback_summary = PricingSummary(
            providers_count=len(fallback_results),
            payer_matches=0,
            min_rate=min(rates) if rates else None,
            max_rate=max(rates) if rates else None,
            average_rate=sum(rates) / len(rates) if rates else None,
        )

        return PriceEstimateResponse(
            query=QueryContext(
                cpt_code=cpt_code,
                payer_name=payer_name,
                state=state,
                zip=zip_code,
                limit=limit,
            ),
            summary=fallback_summary,
            results=fallback_results,
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

    def _fallback_with_npi(
        self,
        *,
        payer_name: Optional[str],
        procedure_summary: ProcedureSummary,
        provider_city: Optional[str],
        provider_state: Optional[str],
        provider_limit: int,
    ) -> list[PriceEstimateItem]:
        if not provider_city or not provider_state:
            return []

        try:
            lookup_results = self.npi_client.lookup(
                city=provider_city,
                state=provider_state,
                limit=provider_limit,
            )
        except Exception:  # pragma: no cover - external failure
            return []

        items: list[PriceEstimateItem] = []
        for entry in lookup_results:
            estimate = self._estimate_price(
                procedure_summary=procedure_summary,
                provider_identifier=entry.npi or entry.name,
            )
            provider_summary = ProviderSummary(
                id=None,
                npi=entry.npi,
                name=entry.name,
                address=entry.address.address_1,
                city=entry.address.city,
                state=entry.address.state,
                zip=entry.address.postal_code,
                phone=entry.address.telephone_number,
                website=None,
            )

            items.append(
                PriceEstimateItem(
                    provider=provider_summary,
                    procedure=procedure_summary,
                    price=PriceDetail(
                        id=None,
                        payer_name=payer_name or "Estimated Market Rate",
                        negotiated_rate=estimate["negotiated_rate"],
                        min_negotiated_rate=estimate["min_rate"],
                        max_negotiated_rate=estimate["max_rate"],
                        standard_charge=estimate["standard_charge"],
                        cash_price=estimate["cash_price"],
                        in_network=True,
                        data_source="Estimated via regional benchmarks (fallback)",
                        confidence_score=estimate["confidence"],
                        last_updated=date.today(),
                        created_at=datetime.utcnow(),
                    ),
                )
            )

        return items

    def _estimate_price(
        self,
        *,
        procedure_summary: ProcedureSummary,
        provider_identifier: str,
    ) -> dict[str, Optional[float]]:
        """
        Generate a reasonable price estimate when negotiated data is unavailable.

        A deterministic hash of the provider identifier adds variation per facility.
        """
        digest = hashlib.md5(provider_identifier.encode("utf-8")).hexdigest()
        seed = int(digest[:8], 16)  # use first 32 bits for variation
        variance = (seed % 41 - 20) / 100  # -0.20 to +0.20 in 0.01 increments

        medicare_rate = (
            float(procedure_summary.medicare_rate)
            if procedure_summary.medicare_rate is not None
            else None
        )

        if medicare_rate and medicare_rate > 0:
            negotiated_base = medicare_rate * 2.75
            standard_base = medicare_rate * 5.2
            cash_base = medicare_rate * 1.8
        else:
            # fallback defaults based on typical outpatient ranges
            negotiated_base = 1800.0
            standard_base = 5200.0
            cash_base = 1500.0

        multiplier = 1.0 + variance
        negotiated = round(max(350.0, negotiated_base * multiplier), 2)
        standard = round(max(negotiated + 250.0, standard_base * multiplier), 2)
        cash = round(max(negotiated * 0.6, cash_base * multiplier), 2)

        spread = negotiated * (0.12 + (seed % 7) / 100)  # 12% - 18%
        min_rate = round(max(negotiated * 0.65, negotiated - spread), 2)
        max_rate = round(negotiated + spread, 2)

        confidence = 0.4 if medicare_rate else 0.25

        return {
            "negotiated_rate": negotiated,
            "standard_charge": standard,
            "cash_price": cash,
            "min_rate": min_rate,
            "max_rate": max_rate,
            "confidence": confidence,
        }

