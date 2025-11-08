from __future__ import annotations

from typing import Dict, List, Optional

from ..schemas.estimate import (
    EstimateRequest,
    EstimateResponse,
    FacilityEstimate,
    ServiceEstimate,
)
from .insurance import InsuranceMatch, InsuranceMatcher, StubInsuranceMatcher
from .types import PriceQuote, ProviderCandidate, PricingRepository, ProviderRepository


class CostEstimator:
    """Coordinates provider lookup and pricing aggregation."""

    def __init__(
        self,
        provider_repo: ProviderRepository,
        pricing_repo: PricingRepository,
        insurance_matcher: Optional[InsuranceMatcher] = None,
    ) -> None:
        self._providers = provider_repo
        self._pricing = pricing_repo
        self._insurance = insurance_matcher or StubInsuranceMatcher()

    async def estimate(self, request: EstimateRequest) -> EstimateResponse:
        providers = list(
            await self._providers.search(
                zip=request.zip,
                radius=request.radius,
                include_out_of_network=request.include_out_of_network,
            )
        )
        if not providers:
            return EstimateResponse()

        insurance_match: Optional[InsuranceMatch] = None
        if request.insurance:
            try:
                insurance_match = await self._insurance.match(request.insurance)
            except Exception:
                insurance_match = None

        payer_name = insurance_match.payer_name if insurance_match else request.insurance
        provider_ids = [p.provider_id for p in providers]
        quotes = list(
            await self._pricing.quotes_for(
                provider_ids=provider_ids,
                cpt_code=request.cpt_code,
                insurance=payer_name,
            )
        )

        quotes_by_provider: Dict[str, List[PriceQuote]] = {}
        for quote in quotes:
            quotes_by_provider.setdefault(quote.provider_id, []).append(quote)

        results: Dict[str, List[FacilityEstimate]] = {}
        for provider in providers:
            facility_quotes = quotes_by_provider.get(provider.provider_id)
            if not facility_quotes:
                continue

            services = [
                ServiceEstimate(
                    cpt_code=quote.cpt_code,
                    negotiated_rate=quote.rate,
                    patient_responsibility=self._patient_responsibility(
                        quote.rate, insurance_match
                    ),
                )
                for quote in facility_quotes
            ]
            first_quote = facility_quotes[0]
            facility = FacilityEstimate(
                facility=provider.name,
                distance_miles=provider.distance_miles,
                services=services,
                source=first_quote.source,
                confidence=first_quote.confidence,
                coverage_percent=insurance_match.coverage_percent
                if insurance_match
                else None,
            )
            results.setdefault(provider.state, []).append(facility)

        return EstimateResponse(results=results)

    def _patient_responsibility(
        self, negotiated_rate: float, match: Optional[InsuranceMatch]
    ) -> Optional[float]:
        if match is None or match.coverage_percent is None:
            return None
        coverage = match.coverage_percent
        coverage = max(0.0, min(coverage, 1.0))
        patient_share = negotiated_rate * (1 - coverage)
        if match.deductible and match.deductible > 0:
            patient_share = min(negotiated_rate, patient_share + match.deductible * 0.1)
        return round(patient_share, 2)


class StubProviderRepository:
    """In-memory provider store for early demos."""

    def __init__(self) -> None:
        self._providers = [
            ProviderCandidate("prov-1", "Mercy Hospital - Joplin", "MO", 11.2),
            ProviderCandidate("prov-2", "Freeman Imaging Center", "MO", 18.7),
            ProviderCandidate("prov-3", "Mercy Hospital - Rogers", "AR", 32.1),
        ]

    async def search(
        self,
        *,
        zip: str,
        radius: int,
        include_out_of_network: bool,
    ) -> Iterable[ProviderCandidate]:
        _ = (zip, radius, include_out_of_network)
        return self._providers


class StubPricingRepository:
    """Static pricing quotes keyed by provider and CPT code."""

    def __init__(self) -> None:
        self._quotes = [
            PriceQuote("prov-1", "73721", 350.0, "hospital_mrf", 0.92),
            PriceQuote("prov-1", "73723", 525.0, "hospital_mrf", 0.9),
            PriceQuote("prov-2", "73721", 370.0, "openmedprices", 0.65),
            PriceQuote("prov-3", "73721", 410.0, "medicare_baseline", 0.5),
        ]

    async def quotes_for(
        self, *, provider_ids: Iterable[str], cpt_code: str, insurance: str
    ) -> Iterable[PriceQuote]:
        _ = insurance
        provider_set = set(provider_ids)
        return [
            quote
            for quote in self._quotes
            if quote.provider_id in provider_set and quote.cpt_code == cpt_code
        ]
