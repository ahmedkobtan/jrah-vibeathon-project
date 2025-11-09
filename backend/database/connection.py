"""
Database connection management
Supports both SQLite (dev) and PostgreSQL (production)
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from .schema import Base


class DatabaseManager:
    """Manage database connections and sessions"""
    
    def __init__(self, database_url: str = None):
        """
        Initialize database manager
        
        Args:
            database_url: Database connection string
                         Defaults to SQLite in-memory for testing
        """
        if database_url is None:
            # Default to SQLite file in backend directory
            db_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 
                'data', 
                'healthcare_prices.db'
            )
            database_url = f"sqlite:///{db_path}"
        
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True  # Verify connections before using
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def create_tables(self):
        """Create all tables in the database"""
        Base.metadata.create_all(bind=self.engine)
        print(f"✓ Database tables created at: {self.database_url}")
    
    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(bind=self.engine)
        print(f"✓ Database tables dropped")
    
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope for database operations
        
        Usage:
            with db.session_scope() as session:
                session.add(provider)
                session.commit()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Global database manager instance
_db_manager = None


def get_db_manager(database_url: str = None) -> DatabaseManager:
    """Get or create the global database manager"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(database_url)
    return _db_manager


def init_database(database_url: str = None, drop_existing: bool = False):
    """
    Initialize the database
    
    Args:
        database_url: Database connection string
        drop_existing: If True, drop all tables before creating
    """
    db = get_db_manager(database_url)
    
    if drop_existing:
        db.drop_tables()
    
    db.create_tables()
    return db
