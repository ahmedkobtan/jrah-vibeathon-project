"""
Database package initialization
"""

from .connection import DatabaseManager, get_db_manager, init_database
from .schema import (
    Base,
    Provider,
    Procedure,
    InsurancePlan,
    PriceTransparency,
    FileProcessingLog,
    QueryLog
)

# Create a global database manager instance for the application
_db_manager = get_db_manager()
SessionLocal = _db_manager.SessionLocal
engine = _db_manager.engine

__all__ = [
    'Base',
    'Provider',
    'Procedure',
    'InsurancePlan',
    'PriceTransparency',
    'FileProcessingLog',
    'QueryLog',
    'DatabaseManager',
    'get_db_manager',
    'init_database',
    'SessionLocal',
    'engine',
]
