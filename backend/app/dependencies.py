"""
FastAPI dependency injection utilities.
"""

from typing import Generator, Optional

from sqlalchemy.orm import Session

from database import SessionLocal
from app.config import settings
from app.services import DuckDuckGoSearchClient, GoogleSearchClient


def get_db() -> Generator[Session, None, None]:
    """
    Provide a database session for each request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_search_client() -> Optional[DuckDuckGoSearchClient | GoogleSearchClient]:
    """
    Provide a search client instance (DuckDuckGo or Google).
    
    Priority:
    1. DuckDuckGo (if available) - No API key needed, preferred!
    2. Google Custom Search (if configured with API keys)
    3. None (will use algorithmic estimates)
    """
    # Try DuckDuckGo first (no API key required!)
    try:
        return DuckDuckGoSearchClient()
    except ImportError:
        pass  # duckduckgo-search not installed
    
    # Fall back to Google Search if configured
    if settings.google_search_enabled:
        return GoogleSearchClient(
            api_key=settings.GOOGLE_SEARCH_API_KEY,
            cse_id=settings.GOOGLE_SEARCH_CSE_ID,
        )
    
    # No search client available
    return None


# Keep legacy function for backward compatibility
def get_google_search_client() -> Optional[GoogleSearchClient]:
    """
    Provide a GoogleSearchClient instance if configured, otherwise None.
    
    Deprecated: Use get_search_client() instead.
    """
    if settings.google_search_enabled:
        return GoogleSearchClient(
            api_key=settings.GOOGLE_SEARCH_API_KEY,
            cse_id=settings.GOOGLE_SEARCH_CSE_ID,
        )
    return None
