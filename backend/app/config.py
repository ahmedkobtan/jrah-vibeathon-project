"""
Application configuration loaded from environment variables.
"""

import os
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///data/healthcare_prices.db"
    )
    
    # Google Custom Search API (Optional)
    GOOGLE_SEARCH_API_KEY: Optional[str] = os.getenv("GOOGLE_SEARCH_API_KEY") or None
    GOOGLE_SEARCH_CSE_ID: Optional[str] = os.getenv("GOOGLE_SEARCH_CSE_ID") or None
    
    @property
    def google_search_enabled(self) -> bool:
        """Check if Google Search API is configured."""
        return bool(self.GOOGLE_SEARCH_API_KEY and self.GOOGLE_SEARCH_CSE_ID)


# Global settings instance
settings = Settings()

