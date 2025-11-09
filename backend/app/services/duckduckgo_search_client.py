"""
DuckDuckGo search client for healthcare pricing lookups.
No API key required - completely free!
"""

from __future__ import annotations

import re
from typing import List, Optional
from dataclasses import dataclass

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None


@dataclass
class SearchResult:
    """A single search result with extracted pricing information."""
    
    title: str
    url: str
    snippet: str
    extracted_prices: List[float]
    provider_name: Optional[str] = None
    location: Optional[str] = None


class DuckDuckGoSearchClient:
    """
    Client for DuckDuckGo search focused on healthcare pricing.
    
    Advantages:
    - No API key required!
    - No rate limits (within reasonable usage)
    - Privacy-focused
    - Free forever
    """
    
    def __init__(self, *, timeout: float = 10.0):
        """
        Initialize the DuckDuckGo Search client.
        
        Args:
            timeout: Request timeout in seconds
        """
        if DDGS is None:
            raise ImportError(
                "duckduckgo-search is required. Install it with: "
                "pip install duckduckgo-search"
            )
        self.timeout = timeout
    
    def search_cpt_pricing(
        self,
        *,
        cpt_code: str,
        location: Optional[str] = None,
        state: Optional[str] = None,
        num_results: int = 10,
    ) -> List[SearchResult]:
        """
        Search for pricing information for a specific CPT code.
        
        Args:
            cpt_code: The CPT code to search for
            location: Optional city name to include in search
            state: Optional state abbreviation to include in search
            num_results: Maximum number of results to return
            
        Returns:
            List of SearchResult objects with extracted pricing data
        """
        # Build search query
        query_parts = [f"CPT {cpt_code}", "cost", "price"]
        
        if location and state:
            query_parts.append(f"{location} {state}")
        elif state:
            query_parts.append(state)
        
        # Add terms to find healthcare pricing pages
        query_parts.append("hospital OR facility OR healthcare")
        
        query = " ".join(query_parts)
        
        try:
            with DDGS() as ddgs:
                # Perform search
                search_results = ddgs.text(
                    keywords=query,
                    region='wt-wt',  # Worldwide, no tracking
                    safesearch='moderate',
                    max_results=num_results,
                )
                
                # Convert to list if it's a generator
                if search_results:
                    search_results = list(search_results)
                else:
                    search_results = []
            
            return self._parse_results(search_results, cpt_code)
            
        except Exception:
            # Return empty list on error rather than failing
            return []
    
    def _parse_results(
        self,
        search_data: list,
        cpt_code: str,
    ) -> List[SearchResult]:
        """
        Parse DuckDuckGo search results and extract pricing information.
        
        Args:
            search_data: List of search result dictionaries from DuckDuckGo
            cpt_code: The CPT code being searched for (for validation)
            
        Returns:
            List of SearchResult objects with extracted data
        """
        results = []
        
        for item in search_data:
            title = item.get("title", "")
            url = item.get("href", "")
            snippet = item.get("body", "")
            
            # Extract prices from snippet and title
            prices = self._extract_prices(f"{title} {snippet}")
            
            # Extract provider name (simple heuristic)
            provider_name = self._extract_provider_name(title, url)
            
            # Extract location info
            location = self._extract_location(snippet)
            
            if prices or provider_name:  # Only include if we found something useful
                results.append(
                    SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        extracted_prices=prices,
                        provider_name=provider_name,
                        location=location,
                    )
                )
        
        return results
    
    def _extract_prices(self, text: str) -> List[float]:
        """
        Extract dollar amounts from text.
        
        Looks for patterns like:
        - $1,234.56
        - $1234
        - 1,234.56
        """
        # Pattern to match dollar amounts
        price_pattern = r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        
        matches = re.findall(price_pattern, text)
        prices = []
        
        for match in matches:
            try:
                # Remove commas and convert to float
                price = float(match.replace(",", ""))
                # Filter reasonable healthcare prices ($50 to $1,000,000)
                if 50 <= price <= 1_000_000:
                    prices.append(price)
            except ValueError:
                continue
        
        return prices
    
    def _extract_provider_name(self, title: str, url: str) -> Optional[str]:
        """
        Extract provider/hospital name from title or URL.
        
        This is a simple heuristic - looks for common patterns.
        """
        # Common hospital/healthcare keywords
        healthcare_keywords = [
            "hospital",
            "medical center",
            "health system",
            "clinic",
            "healthcare",
        ]
        
        # Check title for provider name (first part before separator)
        title_parts = re.split(r"[|\-–—:]", title)
        if title_parts:
            first_part = title_parts[0].strip()
            # If it contains healthcare keywords, it's likely a provider name
            if any(keyword in first_part.lower() for keyword in healthcare_keywords):
                return first_part
        
        # Try to extract from domain
        domain_match = re.search(r"https?://(?:www\.)?([^/]+)", url)
        if domain_match:
            domain = domain_match.group(1)
            # Clean up domain to make it readable
            domain_cleaned = (
                domain.replace(".com", "")
                .replace(".org", "")
                .replace(".net", "")
                .replace("-", " ")
                .title()
            )
            return domain_cleaned
        
        return None
    
    def _extract_location(self, text: str) -> Optional[str]:
        """
        Extract location information from text.
        
        Looks for city, state patterns.
        """
        # Pattern for city, state (e.g., "Los Angeles, CA" or "New York, NY")
        location_pattern = r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})"
        
        match = re.search(location_pattern, text)
        if match:
            return f"{match.group(1)}, {match.group(2)}"
        
        return None
    
    def aggregate_pricing_estimate(
        self,
        search_results: List[SearchResult],
    ) -> dict[str, Optional[float]]:
        """
        Aggregate pricing data from multiple search results.
        
        Returns:
            Dictionary with min, max, average, median, and confidence score
        """
        all_prices = []
        for result in search_results:
            all_prices.extend(result.extracted_prices)
        
        if not all_prices:
            return {
                "min": None,
                "max": None,
                "average": None,
                "median": None,
                "confidence": 0.0,
            }
        
        all_prices.sort()
        n = len(all_prices)
        
        # Calculate median
        if n % 2 == 0:
            median = (all_prices[n // 2 - 1] + all_prices[n // 2]) / 2
        else:
            median = all_prices[n // 2]
        
        # Confidence based on number of data points and variance
        confidence = min(0.7, 0.3 + (n / 20))  # 0.3-0.7 based on sample size
        
        # If variance is high, reduce confidence
        if n > 1:
            variance = sum((p - (sum(all_prices) / n)) ** 2 for p in all_prices) / n
            std_dev = variance ** 0.5
            avg = sum(all_prices) / n
            coefficient_of_variation = std_dev / avg if avg > 0 else 0
            
            # High variance reduces confidence
            if coefficient_of_variation > 0.5:
                confidence *= 0.7
        
        return {
            "min": round(min(all_prices), 2),
            "max": round(max(all_prices), 2),
            "average": round(sum(all_prices) / n, 2),
            "median": round(median, 2),
            "confidence": round(confidence, 2),
        }

