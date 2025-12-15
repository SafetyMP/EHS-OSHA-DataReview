"""
Database Models and Setup
SQLAlchemy models for storing multi-agency compliance data.
"""

import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy import Index, create_engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.types import TypeDecorator, Date
from pathlib import Path
from typing import Optional
from datetime import datetime, date
import os

Base = declarative_base()


class SQLiteDate(TypeDecorator):
    """
    Custom date type that handles SQLite's string-based date storage.
    
    SQLite stores dates as strings, and SQLAlchemy needs help parsing them.
    This decorator stores dates as strings in SQLite but converts them to
    Python date objects when reading from the database.
    
    Handles various date string formats including:
    - 'YYYY-MM-DD'
    - 'YYYY-MM-DD HH:MM:SS'
    - 'YYYY-MM-DD HH:MM:SS.ffffff'
    """
    # Use String as the underlying type for SQLite to avoid SQLAlchemy's date processor
    impl = sa.String
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        """Use String for SQLite, Date for other databases."""
        if dialect.name == 'sqlite':
            return dialect.type_descriptor(sa.String())
        else:
            return dialect.type_descriptor(Date())
    
    def process_bind_param(self, value, dialect):
        """Convert Python date/datetime to string for SQLite."""
        if value is None:
            return None
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, str):
            # Already a string, return as-is
            return value
        return value
    
    def process_result_value(self, value, dialect):
        """Convert SQLite string to Python date object."""
        if value is None:
            return None
        
        # If already a date object (from PostgreSQL or other DBs), return as-is
        if isinstance(value, date):
            return value
        
        # If it's a datetime, extract the date
        if isinstance(value, datetime):
            return value.date()
        
        # Parse string formats (for SQLite)
        if isinstance(value, str):
            # Strip whitespace
            value = value.strip()
            if not value:
                return None
            
            # Try various formats
            formats = [
                '%Y-%m-%d',                    # '1974-03-14'
                '%Y-%m-%d %H:%M:%S',           # '1974-03-14 00:00:00'
                '%Y-%m-%d %H:%M:%S.%f',        # '1974-03-14 00:00:00.000000'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.date()
                except ValueError:
                    continue
            
            # If all formats fail, try pandas parsing as fallback
            try:
                import pandas as pd
                dt = pd.to_datetime(value, errors='coerce')
                if pd.notna(dt):
                    return dt.date()
            except ImportError:
                pass
            
            # Last resort: try ISO format (handles timezone-aware strings)
            try:
                # Remove timezone info if present
                value_clean = value.replace('Z', '+00:00')
                if '+' in value_clean or value_clean.endswith('-00:00'):
                    dt = datetime.fromisoformat(value_clean)
                else:
                    # Try without timezone
                    dt = datetime.fromisoformat(value_clean.split('.')[0])
                return dt.date()
            except (ValueError, AttributeError):
                pass
        
        # If we can't parse it, return None (will be treated as NULL)
        return None


class Inspection(Base):
    """OSHA inspection records."""
    __tablename__ = 'inspections'
    
    id = sa.Column(sa.Integer, primary_key=True)
    activity_nr = sa.Column(sa.String(50), unique=True, nullable=False, index=True)
    estab_name = sa.Column(sa.String(500), index=True)
    site_state = sa.Column(sa.String(2), index=True)
    naics_code = sa.Column(sa.String(10), index=True)
    open_date = sa.Column(SQLiteDate, index=True)
    close_case_date = sa.Column(SQLiteDate)
    year = sa.Column(sa.Integer, index=True)
    inspection_type = sa.Column(sa.String(100))
    
    # Relationships - removed to avoid foreign key issues (violations link via activity_nr string, not FK)
    # violations = sa.orm.relationship("Violation", back_populates="inspection")
    
    __table_args__ = (
        Index('idx_inspection_state_year', 'site_state', 'year'),
        Index('idx_inspection_naics', 'naics_code', 'year'),
    )


class Violation(Base):
    """Violation records from all agencies."""
    __tablename__ = 'violations'
    
    id = sa.Column(sa.Integer, primary_key=True)
    
    # Agency identification
    agency = sa.Column(sa.String(50), nullable=False, index=True)
    
    # Company/Facility information
    company_name = sa.Column(sa.String(500), index=True)  # Original name
    company_name_normalized = sa.Column(sa.String(500), index=True)  # Normalized for matching
    
    # OSHA-specific fields
    activity_nr = sa.Column(sa.String(50), index=True)  # Links to inspection via activity_nr
    standard = sa.Column(sa.String(50), index=True)
    viol_type = sa.Column(sa.String(50))
    description = sa.Column(sa.Text)
    
    # Penalty information
    initial_penalty = sa.Column(sa.Float)
    current_penalty = sa.Column(sa.Float, index=True)
    fta_penalty = sa.Column(sa.Float)
    
    # Location information
    site_state = sa.Column(sa.String(2), index=True)
    site_city = sa.Column(sa.String(100))
    
    # Industry information
    naics_code = sa.Column(sa.String(10), index=True)
    sic_code = sa.Column(sa.String(10))
    
    # Date information
    violation_date = sa.Column(SQLiteDate, index=True)
    year = sa.Column(sa.Integer, index=True)
    
    # Generic fields for other agencies
    facility_id = sa.Column(sa.String(100))  # EPA/MSHA facility/mine ID
    violation_type = sa.Column(sa.String(100))  # Generic violation type
    enforcement_action = sa.Column(sa.String(200))
    
    # Relationships - removed to avoid foreign key issues (violations link via activity_nr string, not FK)
    # inspection = sa.orm.relationship("Inspection", back_populates="violations")
    
    __table_args__ = (
        Index('idx_violation_agency_company', 'agency', 'company_name_normalized'),
        Index('idx_violation_company_year', 'company_name_normalized', 'year'),
        Index('idx_violation_state_year', 'site_state', 'year'),
        Index('idx_violation_agency_year', 'agency', 'year'),
        Index('idx_violation_penalty', 'current_penalty'),  # For penalty filtering
        Index('idx_violation_standard_agency', 'standard', 'agency'),  # For standard lookups
        Index('idx_violation_naics_year', 'naics_code', 'year'),  # For industry analysis
    )


class Accident(Base):
    """Accident records (currently OSHA-specific)."""
    __tablename__ = 'accidents'
    
    id = sa.Column(sa.Integer, primary_key=True)
    accident_key = sa.Column(sa.String(50), unique=True, nullable=False, index=True)
    activity_nr = sa.Column(sa.String(50), index=True)
    estab_name = sa.Column(sa.String(500), index=True)
    site_state = sa.Column(sa.String(2), index=True)
    naics_code = sa.Column(sa.String(10), index=True)
    accident_date = sa.Column(SQLiteDate, index=True)
    year = sa.Column(sa.Integer, index=True)
    description = sa.Column(sa.Text)
    fatality = sa.Column(sa.Boolean)
    injury_type = sa.Column(sa.String(100))


class DatabaseManager:
    """Manager for database connections and operations."""
    
    def __init__(self, database_url: Optional[str] = None, data_dir: Optional[Path] = None, 
                 pool_size: int = 10, max_overflow: int = 20):
        """
        Initialize database manager with connection pooling.
        
        Args:
            database_url: SQLAlchemy database URL (e.g., 'sqlite:///data/compliance.db')
                         If None, uses SQLite in data directory
            data_dir: Directory for data files (used if database_url is None)
            pool_size: Number of connections to maintain in pool (default: 10)
            max_overflow: Maximum overflow connections (default: 20)
        """
        if database_url is None:
            if data_dir is None:
                data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            database_url = f"sqlite:///{data_dir / 'compliance.db'}"
        
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        
        # Connection pool configuration
        pool_args = {
            "pool_pre_ping": True,  # Verify connections before using
            "pool_recycle": 3600,   # Recycle connections after 1 hour
        }
        
        # SQLite-specific handling
        if "sqlite" in database_url:
            pool_args["connect_args"] = {"check_same_thread": False}
            # SQLite uses QueuePool (connection pooling still helps with connection reuse)
            self.engine = create_engine(
                database_url,
                echo=False,
                poolclass=QueuePool,
                **pool_args
            )
        else:
            # PostgreSQL/other databases support connection pooling
            pool_args.update({
                "pool_size": pool_size,
                "max_overflow": max_overflow,
            })
            self.engine = create_engine(
                database_url,
                echo=False,
                **pool_args
            )
        
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.bind = self.engine
    
    def create_tables(self):
        """Create all database tables including summary tables."""
        Base.metadata.create_all(self.engine)
        
        # Also create summary tables if the module is available
        try:
            from .summary_tables import SummaryTableManager
            summary_manager = SummaryTableManager(self)
            summary_manager.create_tables()
        except ImportError:
            pass  # Summary tables are optional
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)."""
        Base.metadata.drop_all(self.engine)
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    def close(self):
        """Close database connections."""
        self.engine.dispose()
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        return sa.inspect(self.engine).has_table(table_name)
    
    def get_table_row_count(self, table_name: str) -> int:
        """Get row count for a table."""
        with self.engine.connect() as conn:
            result = conn.execute(sa.text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.scalar()
    
    def get_stats(self) -> dict:
        """Get statistics about the database."""
        stats = {
            "database_url": self.database_url,
            "tables": {}
        }
        
        for table_name in ["inspections", "violations", "accidents"]:
            if self.table_exists(table_name):
                stats["tables"][table_name] = {
                    "exists": True,
                    "row_count": self.get_table_row_count(table_name)
                }
            else:
                stats["tables"][table_name] = {"exists": False}
        
        return stats


# Global database manager instance (lazy initialization)
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(database_url: Optional[str] = None, data_dir: Optional[Path] = None, 
                   pool_size: int = 10, max_overflow: int = 20) -> DatabaseManager:
    """Get or create global database manager instance with connection pooling."""
    global _db_manager
    if _db_manager is None:
        # Try to load settings for pool configuration
        try:
            from .config import get_settings
            settings = get_settings()
            pool_size = settings.database_pool_size
            max_overflow = settings.database_max_overflow
            if settings.database_url:
                database_url = settings.database_url
            if not data_dir:
                data_dir = settings.get_data_dir()
        except ImportError:
            pass  # Use defaults if config not available
        
        _db_manager = DatabaseManager(
            database_url=database_url, 
            data_dir=data_dir,
            pool_size=pool_size,
            max_overflow=max_overflow
        )
        _db_manager.create_tables()
    return _db_manager


def reset_db_manager():
    """Reset global database manager (useful for testing)."""
    global _db_manager
    if _db_manager is not None:
        _db_manager.close()
    _db_manager = None

