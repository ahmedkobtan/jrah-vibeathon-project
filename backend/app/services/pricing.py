"""
Pricing service containing business logic for cost estimates.
"""

from datetime import date, datetime
from typing import Optional, Union
import hashlib
import os

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import PriceTransparency, Procedure, Provider
from .npi_client import NpiClient
from .duckduckgo_search_client import DuckDuckGoSearchClient
from .google_search_client import GoogleSearchClient
from app.schemas import (
    PriceDetail,
    PriceEstimateItem,
    PriceEstimateResponse,
    PricingSummary,
    ProcedureSummary,
    ProviderSummary,
    QueryContext,
)

# Import the Pricing Estimation Agent
try:
    from agents.pricing_estimation_agent import PricingEstimationAgent
    from agents.openrouter_llm import OpenRouterLLMClient
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False


class PricingService:
    """
    Encapsulates pricing lookup logic.
    """

    def __init__(
        self,
        session: Session,
        npi_client: NpiClient | None = None,
        search_client: Union[DuckDuckGoSearchClient, GoogleSearchClient, None] = None,
        google_search_client: GoogleSearchClient | None = None,  # Legacy parameter
        use_agent: bool = True,  # NEW: Enable agent-based estimation
    ):
        self.session = session
        self.npi_client = npi_client or NpiClient()
        # Support both new generic search_client and legacy google_search_client
        self.search_client = search_client or google_search_client
        
        # Initialize the Pricing Estimation Agent if available
        self.agent = None
        if use_agent and AGENT_AVAILABLE:
            try:
                api_key = os.getenv("OPENROUTER_API_KEY", "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")
                llm_client = OpenRouterLLMClient(api_key=api_key)
                self.agent = PricingEstimationAgent(
                    llm_client=llm_client,
                    search_client=self.search_client
                )
            except Exception as e:
                print(f"Failed to initialize Pricing Estimation Agent: {e}")
                self.agent = None

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
            state_filter=state,
            zip_filter=zip_code,
        )

        # If NPI fallback didn't yield results, try Web Search (DuckDuckGo or Google)
        if not fallback_results and self.search_client:
            fallback_results = self._fallback_with_web_search(
                procedure_summary=procedure_summary,
                cpt_code=cpt_code,
                payer_name=payer_name,
                provider_city=provider_city,
                provider_state=provider_state,
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
        state_filter: Optional[str] = None,
        zip_filter: Optional[str] = None,
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
            # Apply state filter if provided (redundant but keeps consistency)
            if state_filter and entry.address.state != state_filter.upper():
                continue
            
            # Don't apply ZIP filter when using NPI fallback with city specified.
            # A city typically has multiple ZIP codes, and exact ZIP matching
            # is too restrictive. The provider_city parameter is specific enough.
            
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

    def _fallback_with_web_search(
        self,
        *,
        procedure_summary: ProcedureSummary,
        cpt_code: str,
        payer_name: Optional[str],
        provider_city: Optional[str],
        provider_state: Optional[str],
    ) -> list[PriceEstimateItem]:
        """
        Use web search (DuckDuckGo or Google) and AI agent to find pricing information.
        
        This is the last-resort fallback when:
        - No database records exist
        - NPI fallback didn't produce results
        - Web search client is available (DuckDuckGo preferred, Google as alternative)
        
        NEW: Now uses intelligent Pricing Estimation Agent for better estimates.
        """
        # Try the new agent-based approach first
        if self.agent:
            try:
                estimate_data = self.agent.estimate_price(
                    cpt_code=cpt_code,
                    procedure_description=procedure_summary.description,
                    state=provider_state,
                    city=provider_city,
                    payer_name=payer_name,
                    use_llm_analysis=True  # Enable LLM for better analysis
                )
                
                if estimate_data and estimate_data.get("negotiated_rate"):
                    # Create a provider summary for the agent-based estimate
                    location_str = f"{provider_city}, {provider_state}" if provider_city and provider_state else provider_state or "Unknown"
                    
                    provider_summary = ProviderSummary(
                        id=None,
                        npi=None,
                        name=f"AI-Estimated Average ({location_str})",
                        address="Web-sourced + AI analyzed estimate",
                        city=provider_city or "",
                        state=provider_state or "",
                        zip="",
                        phone=None,
                        website=None,
                    )
                    
                    # Build detailed data source description
                    data_source = estimate_data.get("data_source", "AI Agent Estimate")
                    if estimate_data.get("analysis"):
                        data_source += f" | {estimate_data['analysis']}"
                    
                    price_detail = PriceDetail(
                        id=None,
                        payer_name=payer_name or "Market Average",
                        negotiated_rate=estimate_data["negotiated_rate"],
                        min_negotiated_rate=estimate_data.get("min_rate"),
                        max_negotiated_rate=estimate_data.get("max_rate"),
                        standard_charge=estimate_data.get("standard_charge"),
                        cash_price=estimate_data.get("cash_price"),
                        in_network=True,
                        data_source=data_source,
                        confidence_score=estimate_data.get("confidence", 0.5),
                        last_updated=date.today(),
                        created_at=datetime.utcnow(),
                    )
                    
                    return [
                        PriceEstimateItem(
                            provider=provider_summary,
                            procedure=procedure_summary,
                            price=price_detail,
                        )
                    ]
            except Exception as e:
                print(f"Agent-based estimation failed: {e}")
                # Fall through to legacy method
        
        # Fallback to old method if agent is not available
        if not self.search_client:
            return []
        
        # Determine search engine name for display
        search_engine = "DuckDuckGo" if isinstance(self.search_client, DuckDuckGoSearchClient) else "Google Search"
        
        try:
            # Search for pricing information (same interface for both clients)
            search_results = self.search_client.search_cpt_pricing(
                cpt_code=cpt_code,
                location=provider_city,
                state=provider_state,
                num_results=10,
            )
            
            if not search_results:
                return []
            
            # Aggregate pricing data from search results
            aggregated = self.search_client.aggregate_pricing_estimate(
                search_results
            )
            
            # If we got useful pricing data, create a single estimate item
            if aggregated["average"] is not None:
                # Use the median as the primary estimate (more robust than average)
                primary_estimate = aggregated["median"] or aggregated["average"]
                
                location_str = f"{provider_city}, {provider_state}" if provider_city and provider_state else provider_state or "Unknown"
                
                # Create a synthetic provider summary for the search-based estimate
                provider_summary = ProviderSummary(
                    id=None,
                    npi=None,
                    name=f"Regional Average ({location_str})",
                    address="Web-sourced estimate",
                    city=provider_city or "",
                    state=provider_state or "",
                    zip="",
                    phone=None,
                    website=None,
                )
                
                # Create the price detail
                price_detail = PriceDetail(
                    id=None,
                    payer_name=payer_name or "Market Average",
                    negotiated_rate=primary_estimate,
                    min_negotiated_rate=aggregated["min"],
                    max_negotiated_rate=aggregated["max"],
                    standard_charge=aggregated["max"],  # Use max as standard charge
                    cash_price=primary_estimate * 0.8 if primary_estimate else None,  # Estimate cash at 80% of negotiated
                    in_network=True,
                    data_source=f"{search_engine} (n={len(search_results)} sources)",
                    confidence_score=aggregated["confidence"],
                    last_updated=date.today(),
                    created_at=datetime.utcnow(),
                )
                
                return [
                    PriceEstimateItem(
                        provider=provider_summary,
                        procedure=procedure_summary,
                        price=price_detail,
                    )
                ]
                
        except Exception:  # pragma: no cover - external API failure
            # Silently fail and return empty list if search fails
            pass
        
        return []
    
    # Keep old method name for backward compatibility
    def _fallback_with_google_search(self, **kwargs):
        """Deprecated: Use _fallback_with_web_search instead."""
        return self._fallback_with_web_search(**kwargs)

