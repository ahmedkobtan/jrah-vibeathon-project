"""
Shared FastAPI dependencies.
"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from database.connection import get_db_manager


def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session for FastAPI routes.

    Ensures sessions are properly closed after the request lifecycle.
    """
    db_manager = get_db_manager()
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

