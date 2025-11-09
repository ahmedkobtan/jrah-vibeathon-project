"""
Pricing Estimation Agent - Intelligent medical bill estimation using web search and LLM
"""

import os
import json
import re
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

try:
    from app.services.duckduckgo_search_client import DuckDuckGoSearchClient, SearchResult
    DUCKDUCKGO_AVAILABLE = True
except ImportError:
    DUCKDUCKGO_AVAILABLE = False

try:
    from app.services.google_search_client import GoogleSearchClient
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


class PricingEstimationAgent:
    """
    Intelligent agent for estimating medical bills using web search and LLM analysis.
    
    This agent:
    - Searches the web (DuckDuckGo and Google) for pricing information
    - Uses LLM to analyze and validate pricing data
    - Considers location (state, city) and insurance type
    - Provides confidence scores based on data quality
    - Falls back gracefully when data is unavailable
    """
    
    def __init__(
        self, 
        llm_client=None,
        search_client=None,
        use_duckduckgo: bool = True,
        use_google: bool = True
    ):
        """
        Initialize the Pricing Estimation Agent.
        
        Args:
            llm_client: LLM client for intelligent analysis (OpenRouter, etc.)
            search_client: Optional pre-configured search client
            use_duckduckgo: Whether to try DuckDuckGo search (default: True)
            use_google: Whether to try Google search as fallback (default: True)
        """
        self.llm = llm_client
        self.use_duckduckgo = use_duckduckgo
        self.use_google = use_google
        
        # Initialize search client if not provided
        if search_client:
            self.search_client = search_client
        else:
            self.search_client = self._initialize_search_client()
        
        logger.info(f"PricingEstimationAgent initialized (DDG: {use_duckduckgo}, Google: {use_google})")
    
    def _initialize_search_client(self):
        """Initialize the best available search client."""
        # Try DuckDuckGo first (no API key required)
        if self.use_duckduckgo and DUCKDUCKGO_AVAILABLE:
            try:
                return DuckDuckGoSearchClient()
            except Exception as e:
                logger.warning(f"Failed to initialize DuckDuckGo client: {e}")
        
        # Fall back to Google if available and configured
        if self.use_google and GOOGLE_AVAILABLE:
            try:
                from app.config import settings
                if settings.google_search_enabled:
                    return GoogleSearchClient(
                        api_key=settings.GOOGLE_SEARCH_API_KEY,
                        cse_id=settings.GOOGLE_SEARCH_CSE_ID
                    )
            except Exception as e:
                logger.warning(f"Failed to initialize Google Search client: {e}")
        
        return None
    
    def estimate_price(
        self,
        *,
        cpt_code: str,
        procedure_description: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        payer_name: Optional[str] = None,
        use_llm_analysis: bool = True
    ) -> Dict:
        """
        Estimate the price for a medical procedure using web search and LLM.
        
        Args:
            cpt_code: The CPT code for the procedure
            procedure_description: Optional description of the procedure
            state: State code (e.g., "MO")
            city: City name (e.g., "Joplin")
            zip_code: ZIP code
            payer_name: Insurance payer name
            use_llm_analysis: Whether to use LLM for intelligent analysis
        
        Returns:
            Dictionary with estimated pricing data:
            {
                "negotiated_rate": float,
                "min_rate": float,
                "max_rate": float,
                "cash_price": float,
                "standard_charge": float,
                "confidence": float,
                "data_source": str,
                "source_count": int,
                "analysis": str (if LLM used)
            }
        """
        logger.info(f"Estimating price for CPT {cpt_code} in {city}, {state}")
        
        # Step 1: Perform web search
        search_results = self._perform_web_search(
            cpt_code=cpt_code,
            city=city,
            state=state
        )
        
        if not search_results:
            logger.warning(f"No web search results found for CPT {cpt_code}")
            return self._generate_fallback_estimate(cpt_code, state, city)
        
        # Step 2: Extract pricing data from search results
        extracted_prices = self._extract_all_prices(search_results)
        
        if not extracted_prices:
            logger.warning(f"No prices extracted from search results for CPT {cpt_code}")
            return self._generate_fallback_estimate(cpt_code, state, city)
        
        # Step 3: Analyze and aggregate pricing data
        base_estimate = self._aggregate_pricing_data(extracted_prices, len(search_results))
        
        # Step 4: Use LLM for intelligent analysis if available and requested
        if use_llm_analysis and self.llm:
            llm_enhanced = self._llm_analysis(
                cpt_code=cpt_code,
                procedure_description=procedure_description,
                search_results=search_results,
                base_estimate=base_estimate,
                location=f"{city}, {state}" if city and state else state,
                payer_name=payer_name
            )
            if llm_enhanced:
                base_estimate.update(llm_enhanced)
        
        # Step 5: Add metadata
        search_engine = "DuckDuckGo" if isinstance(self.search_client, DuckDuckGoSearchClient) else "Google Search"
        base_estimate["data_source"] = f"{search_engine} + AI Analysis (n={len(search_results)} sources)"
        base_estimate["source_count"] = len(search_results)
        
        logger.info(f"Price estimated: ${base_estimate['negotiated_rate']:.2f} (confidence: {base_estimate['confidence']:.2f})")
        
        return base_estimate
    
    def _perform_web_search(
        self,
        cpt_code: str,
        city: Optional[str],
        state: Optional[str],
        num_results: int = 15
    ) -> List[SearchResult]:
        """Perform web search using available search client."""
        if not self.search_client:
            logger.warning("No search client available")
            return []
        
        try:
            results = self.search_client.search_cpt_pricing(
                cpt_code=cpt_code,
                location=city,
                state=state,
                num_results=num_results
            )
            logger.info(f"Found {len(results)} search results")
            return results
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []
    
    def _extract_all_prices(self, search_results: List[SearchResult]) -> List[float]:
        """Extract all prices from search results."""
        all_prices = []
        for result in search_results:
            if hasattr(result, 'extracted_prices'):
                all_prices.extend(result.extracted_prices)
        
        # Filter out outliers (extreme values)
        if len(all_prices) > 3:
            all_prices = self._remove_outliers(all_prices)
        
        return all_prices
    
    def _remove_outliers(self, prices: List[float]) -> List[float]:
        """Remove statistical outliers using IQR method."""
        if len(prices) < 4:
            return prices
        
        sorted_prices = sorted(prices)
        n = len(sorted_prices)
        
        q1 = sorted_prices[n // 4]
        q3 = sorted_prices[(3 * n) // 4]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        filtered = [p for p in prices if lower_bound <= p <= upper_bound]
        
        if filtered:  # Only return filtered if it's not empty
            logger.debug(f"Removed {len(prices) - len(filtered)} outliers")
            return filtered
        else:
            return prices
    
    def _aggregate_pricing_data(self, prices: List[float], source_count: int) -> Dict:
        """Aggregate pricing data with statistics."""
        if not prices:
            return {
                "negotiated_rate": None,
                "min_rate": None,
                "max_rate": None,
                "cash_price": None,
                "standard_charge": None,
                "confidence": 0.0
            }
        
        # Sort prices
        sorted_prices = sorted(prices)
        n = len(sorted_prices)
        
        # Calculate statistics
        min_price = sorted_prices[0]
        max_price = sorted_prices[-1]
        average = sum(prices) / n
        
        # Calculate median (more robust than average)
        if n % 2 == 0:
            median = (sorted_prices[n // 2 - 1] + sorted_prices[n // 2]) / 2
        else:
            median = sorted_prices[n // 2]
        
        # Use median as primary estimate
        negotiated_rate = median
        
        # Estimate cash price (typically 70-80% of negotiated)
        cash_price = negotiated_rate * 0.75
        
        # Estimate standard charge (typically higher)
        standard_charge = max_price * 1.2
        
        # Calculate confidence score
        confidence = self._calculate_confidence(prices, source_count)
        
        return {
            "negotiated_rate": round(negotiated_rate, 2),
            "min_rate": round(min_price, 2),
            "max_rate": round(max_price, 2),
            "cash_price": round(cash_price, 2),
            "standard_charge": round(standard_charge, 2),
            "confidence": round(confidence, 2)
        }
    
    def _calculate_confidence(self, prices: List[float], source_count: int) -> float:
        """
        Calculate confidence score based on data quality.
        
        Factors:
        - Number of data sources
        - Price variance (lower variance = higher confidence)
        - Number of distinct prices
        """
        if not prices:
            return 0.0
        
        # Base confidence from sample size (0.3 to 0.75)
        source_confidence = min(0.75, 0.3 + (source_count / 25))
        
        # Confidence from number of prices
        price_count_confidence = min(0.8, 0.3 + (len(prices) / 30))
        
        # Reduce confidence for high variance
        if len(prices) > 1:
            mean = sum(prices) / len(prices)
            variance = sum((p - mean) ** 2 for p in prices) / len(prices)
            std_dev = variance ** 0.5
            coefficient_of_variation = std_dev / mean if mean > 0 else 0
            
            # High variance reduces confidence
            if coefficient_of_variation > 0.5:
                variance_penalty = 0.7
            elif coefficient_of_variation > 0.3:
                variance_penalty = 0.85
            else:
                variance_penalty = 1.0
        else:
            variance_penalty = 0.8  # Single data point is less reliable
        
        # Combined confidence
        final_confidence = (source_confidence + price_count_confidence) / 2 * variance_penalty
        
        return max(0.25, min(0.85, final_confidence))  # Clamp between 0.25 and 0.85
    
    def _llm_analysis(
        self,
        cpt_code: str,
        procedure_description: Optional[str],
        search_results: List[SearchResult],
        base_estimate: Dict,
        location: Optional[str],
        payer_name: Optional[str]
    ) -> Dict:
        """
        Use LLM to analyze search results and refine price estimate.
        
        Returns:
            Dictionary with refined estimates and analysis text
        """
        try:
            # Prepare context from search results
            context_snippets = []
            for i, result in enumerate(search_results[:5], 1):
                snippet = f"{i}. {result.title[:80]}"
                if result.extracted_prices:
                    prices_str = ", ".join([f"${p:,.2f}" for p in result.extracted_prices[:3]])
                    snippet += f" | Prices: {prices_str}"
                if result.provider_name:
                    snippet += f" | Provider: {result.provider_name}"
                context_snippets.append(snippet)
            
            context = "\n".join(context_snippets)
            
            prompt = f"""You are a healthcare pricing analyst. Analyze these web search results to refine a medical procedure price estimate.

CPT Code: {cpt_code}
Procedure: {procedure_description or "Unknown"}
Location: {location or "Not specified"}
Insurance: {payer_name or "Not specified"}

Web search findings (top 5 of {len(search_results)} results):
{context}

Initial statistical estimate:
- Median price: ${base_estimate.get('negotiated_rate', 0):,.2f}
- Range: ${base_estimate.get('min_rate', 0):,.2f} - ${base_estimate.get('max_rate', 0):,.2f}
- Confidence: {base_estimate.get('confidence', 0):.0%}

Task: Analyze the context and provide:
1. A refined price estimate (if adjustment is needed)
2. Brief analysis of pricing factors
3. Confidence assessment

Return ONLY a JSON object with this format:
{{
  "adjusted_negotiated_rate": <number or null if no adjustment>,
  "adjusted_confidence": <number between 0.25 and 0.90 or null>,
  "analysis": "<1-2 sentence analysis of pricing factors>",
  "location_factor": "<how location affects pricing>"
}}

Be conservative with adjustments. Only suggest changes if you have strong evidence.
"""
            
            response = self.llm.complete(prompt, temperature=0.3, max_tokens=512)
            
            # Parse LLM response
            parsed = self._parse_llm_response(response)
            
            if parsed:
                result = {}
                
                # Apply adjusted rate if suggested
                if parsed.get("adjusted_negotiated_rate") is not None:
                    adjusted_rate = float(parsed["adjusted_negotiated_rate"])
                    # Only apply if within reasonable range (20% of original)
                    original = base_estimate.get("negotiated_rate", 0)
                    if original > 0 and 0.8 * original <= adjusted_rate <= 1.2 * original:
                        result["negotiated_rate"] = round(adjusted_rate, 2)
                        logger.info(f"LLM adjusted rate: ${original:.2f} -> ${adjusted_rate:.2f}")
                
                # Apply adjusted confidence if suggested
                if parsed.get("adjusted_confidence") is not None:
                    adjusted_conf = float(parsed["adjusted_confidence"])
                    if 0.25 <= adjusted_conf <= 0.90:
                        result["confidence"] = round(adjusted_conf, 2)
                
                # Add analysis text
                if parsed.get("analysis"):
                    result["analysis"] = parsed["analysis"]
                
                if parsed.get("location_factor"):
                    result["location_factor"] = parsed["location_factor"]
                
                return result
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
        
        return {}
    
    def _parse_llm_response(self, response: str) -> Optional[Dict]:
        """Parse LLM JSON response."""
        try:
            # Clean response
            response = response.strip()
            if response.startswith("```"):
                # Extract JSON from code block
                parts = response.split("```")
                for part in parts:
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{"):
                        response = part
                        break
            
            # Parse JSON
            parsed = json.loads(response)
            return parsed
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return None
    
    def _generate_fallback_estimate(
        self,
        cpt_code: str,
        state: Optional[str],
        city: Optional[str]
    ) -> Dict:
        """
        Generate a fallback estimate when web search fails.
        Uses simple heuristics based on typical healthcare pricing.
        """
        # Base estimates by CPT code range (common patterns)
        cpt_num = int(cpt_code) if cpt_code.isdigit() else 99999
        
        # Determine base price by CPT code range
        if 99201 <= cpt_num <= 99215:  # Office visits
            base_price = 150
        elif 70000 <= cpt_num <= 79999:  # Radiology
            base_price = 250
        elif 80000 <= cpt_num <= 89999:  # Lab tests
            base_price = 100
        elif 90000 <= cpt_num <= 99999:  # Medicine
            base_price = 200
        else:  # Surgical procedures
            base_price = 500
        
        # Apply location factor (rough cost-of-living adjustment)
        location_multiplier = self._get_location_multiplier(state, city)
        adjusted_price = base_price * location_multiplier
        
        # Generate range
        min_rate = adjusted_price * 0.7
        max_rate = adjusted_price * 1.5
        cash_price = adjusted_price * 0.75
        standard_charge = adjusted_price * 1.8
        
        return {
            "negotiated_rate": round(adjusted_price, 2),
            "min_rate": round(min_rate, 2),
            "max_rate": round(max_rate, 2),
            "cash_price": round(cash_price, 2),
            "standard_charge": round(standard_charge, 2),
            "confidence": 0.25,  # Low confidence for fallback
            "data_source": "Algorithmic estimate (no web data)",
            "source_count": 0
        }
    
    def _get_location_multiplier(self, state: Optional[str], city: Optional[str]) -> float:
        """
        Get cost-of-living multiplier for location.
        Based on general healthcare cost patterns.
        """
        # High-cost states
        high_cost_states = {"CA", "NY", "MA", "CT", "NJ", "AK", "HI"}
        # Low-cost states
        low_cost_states = {"MS", "AR", "OK", "WV", "AL", "KY"}
        
        if state in high_cost_states:
            return 1.3
        elif state in low_cost_states:
            return 0.85
        else:
            return 1.0  # Average
    
    def batch_estimate(
        self,
        procedures: List[Dict],
        **common_params
    ) -> List[Dict]:
        """
        Estimate prices for multiple procedures at once.
        More efficient than individual estimates.
        
        Args:
            procedures: List of dicts with {"cpt_code": str, "description": str}
            **common_params: Common parameters (state, city, payer_name, etc.)
        
        Returns:
            List of estimate dictionaries
        """
        results = []
        
        for proc in procedures:
            estimate = self.estimate_price(
                cpt_code=proc["cpt_code"],
                procedure_description=proc.get("description"),
                **common_params
            )
            estimate["cpt_code"] = proc["cpt_code"]
            results.append(estimate)
        
        return results

