"""
Pre-aggregated summary tables for fast queries.
These tables store pre-computed aggregations to speed up common queries.
"""

from sqlalchemy import Column, Integer, Float, String, Date, Index, func
from .database import Base
import sqlalchemy as sa
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ViolationSummaryByYear(Base):
    """Pre-aggregated violation statistics by year."""
    __tablename__ = 'violation_summary_by_year'
    
    id = Column(Integer, primary_key=True)
    agency = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False, index=True)
    violation_count = Column(Integer, default=0)
    total_penalties = Column(Float, default=0.0)
    avg_penalty = Column(Float, default=0.0)
    max_penalty = Column(Float)
    min_penalty = Column(Float)
    
    __table_args__ = (
        sa.UniqueConstraint('agency', 'year', name='uq_violation_summary_year'),
        Index('idx_summary_year_agency', 'year', 'agency'),
    )


class ViolationSummaryByState(Base):
    """Pre-aggregated violation statistics by state."""
    __tablename__ = 'violation_summary_by_state'
    
    id = Column(Integer, primary_key=True)
    agency = Column(String(50), nullable=False)
    site_state = Column(String(2), nullable=False, index=True)
    year = Column(Integer, index=True)  # Optional: None = all years
    violation_count = Column(Integer, default=0)
    total_penalties = Column(Float, default=0.0)
    avg_penalty = Column(Float, default=0.0)
    
    __table_args__ = (
        Index('idx_summary_state_year', 'site_state', 'year'),
        Index('idx_summary_state_agency', 'site_state', 'agency'),
    )


class ViolationSummaryByStandard(Base):
    """Pre-aggregated top violations by standard."""
    __tablename__ = 'violation_summary_by_standard'
    
    id = Column(Integer, primary_key=True)
    agency = Column(String(50), nullable=False)
    standard = Column(String(50), nullable=False, index=True)
    year = Column(Integer, index=True)  # Optional: None = all years
    citation_count = Column(Integer, default=0)
    total_penalties = Column(Float, default=0.0)
    avg_penalty = Column(Float, default=0.0)
    
    __table_args__ = (
        Index('idx_summary_standard_year', 'standard', 'year'),
        Index('idx_summary_standard_agency', 'standard', 'agency'),
    )


class ViolationSummaryByCompany(Base):
    """Pre-aggregated violation statistics by company."""
    __tablename__ = 'violation_summary_by_company'
    
    id = Column(Integer, primary_key=True)
    agency = Column(String(50), nullable=False)
    company_name_normalized = Column(String(500), nullable=False, index=True)
    violation_count = Column(Integer, default=0)
    total_penalties = Column(Float, default=0.0)
    avg_penalty = Column(Float, default=0.0)
    first_violation_date = Column(Date)
    last_violation_date = Column(Date)
    years_active = Column(Integer)  # Number of years with violations
    
    __table_args__ = (
        Index('idx_summary_company_agency', 'company_name_normalized', 'agency'),
        Index('idx_summary_company_count', 'violation_count'),  # For sorting
    )


class SummaryTableManager:
    """Manager for creating and refreshing summary tables."""
    
    def __init__(self, db_manager):
        """Initialize with database manager."""
        self.db = db_manager
        self.engine = db_manager.engine
    
    def create_tables(self):
        """Create all summary tables."""
        Base.metadata.create_all(self.engine, tables=[
            ViolationSummaryByYear.__table__,
            ViolationSummaryByState.__table__,
            ViolationSummaryByStandard.__table__,
            ViolationSummaryByCompany.__table__,
        ])
        logger.info("Summary tables created")
    
    def refresh_all_summaries(self, agency: Optional[str] = None):
        """Refresh all summary tables."""
        logger.info("Refreshing all summary tables...")
        self.refresh_year_summary(agency=agency)
        self.refresh_state_summary(agency=agency)
        self.refresh_standard_summary(agency=agency)
        self.refresh_company_summary(agency=agency)
        logger.info("Summary tables refreshed")
    
    def refresh_year_summary(self, agency: Optional[str] = None):
        """Refresh violation summary by year."""
        from .database import Violation
        
        session = self.db.get_session()
        try:
            # Delete existing records
            if agency:
                session.query(ViolationSummaryByYear).filter(
                    ViolationSummaryByYear.agency == agency
                ).delete()
            else:
                session.query(ViolationSummaryByYear).delete()
            
            # Aggregate by year
            query = session.query(
                Violation.agency,
                Violation.year,
                func.count(Violation.id).label('violation_count'),
                func.sum(Violation.current_penalty).label('total_penalties'),
                func.avg(Violation.current_penalty).label('avg_penalty'),
                func.max(Violation.current_penalty).label('max_penalty'),
                func.min(Violation.current_penalty).label('min_penalty')
            ).filter(Violation.year.isnot(None))
            
            if agency:
                query = query.filter(Violation.agency == agency)
            
            results = query.group_by(Violation.agency, Violation.year).all()
            
            # Insert summaries
            for row in results:
                summary = ViolationSummaryByYear(
                    agency=row.agency,
                    year=row.year,
                    violation_count=row.violation_count or 0,
                    total_penalties=row.total_penalties or 0.0,
                    avg_penalty=row.avg_penalty or 0.0,
                    max_penalty=row.max_penalty,
                    min_penalty=row.min_penalty
                )
                session.add(summary)
            
            session.commit()
            logger.info(f"Refreshed year summary: {len(results)} records")
        except Exception as e:
            session.rollback()
            logger.error(f"Error refreshing year summary: {e}")
            raise
        finally:
            session.close()
    
    def refresh_state_summary(self, agency: Optional[str] = None):
        """Refresh violation summary by state."""
        from .database import Violation
        
        session = self.db.get_session()
        try:
            if agency:
                session.query(ViolationSummaryByState).filter(
                    ViolationSummaryByState.agency == agency
                ).delete()
            else:
                session.query(ViolationSummaryByState).delete()
            
            query = session.query(
                Violation.agency,
                Violation.site_state,
                Violation.year,
                func.count(Violation.id).label('violation_count'),
                func.sum(Violation.current_penalty).label('total_penalties'),
                func.avg(Violation.current_penalty).label('avg_penalty')
            ).filter(Violation.site_state.isnot(None))
            
            if agency:
                query = query.filter(Violation.agency == agency)
            
            results = query.group_by(Violation.agency, Violation.site_state, Violation.year).all()
            
            for row in results:
                summary = ViolationSummaryByState(
                    agency=row.agency,
                    site_state=row.site_state,
                    year=row.year,
                    violation_count=row.violation_count or 0,
                    total_penalties=row.total_penalties or 0.0,
                    avg_penalty=row.avg_penalty or 0.0
                )
                session.add(summary)
            
            session.commit()
            logger.info(f"Refreshed state summary: {len(results)} records")
        except Exception as e:
            session.rollback()
            logger.error(f"Error refreshing state summary: {e}")
            raise
        finally:
            session.close()
    
    def refresh_standard_summary(self, agency: Optional[str] = None):
        """Refresh violation summary by standard."""
        from .database import Violation
        
        session = self.db.get_session()
        try:
            if agency:
                session.query(ViolationSummaryByStandard).filter(
                    ViolationSummaryByStandard.agency == agency
                ).delete()
            else:
                session.query(ViolationSummaryByStandard).delete()
            
            query = session.query(
                Violation.agency,
                Violation.standard,
                Violation.year,
                func.count(Violation.id).label('citation_count'),
                func.sum(Violation.current_penalty).label('total_penalties'),
                func.avg(Violation.current_penalty).label('avg_penalty')
            ).filter(Violation.standard.isnot(None)).filter(Violation.standard != "")
            
            if agency:
                query = query.filter(Violation.agency == agency)
            
            results = query.group_by(Violation.agency, Violation.standard, Violation.year).all()
            
            for row in results:
                summary = ViolationSummaryByStandard(
                    agency=row.agency,
                    standard=row.standard,
                    year=row.year,
                    citation_count=row.citation_count or 0,
                    total_penalties=row.total_penalties or 0.0,
                    avg_penalty=row.avg_penalty or 0.0
                )
                session.add(summary)
            
            session.commit()
            logger.info(f"Refreshed standard summary: {len(results)} records")
        except Exception as e:
            session.rollback()
            logger.error(f"Error refreshing standard summary: {e}")
            raise
        finally:
            session.close()
    
    def refresh_company_summary(self, agency: Optional[str] = None):
        """Refresh violation summary by company."""
        from .database import Violation
        
        session = self.db.get_session()
        try:
            if agency:
                session.query(ViolationSummaryByCompany).filter(
                    ViolationSummaryByCompany.agency == agency
                ).delete()
            else:
                session.query(ViolationSummaryByCompany).delete()
            
            query = session.query(
                Violation.agency,
                Violation.company_name_normalized,
                func.count(Violation.id).label('violation_count'),
                func.sum(Violation.current_penalty).label('total_penalties'),
                func.avg(Violation.current_penalty).label('avg_penalty'),
                func.min(Violation.violation_date).label('first_violation_date'),
                func.max(Violation.violation_date).label('last_violation_date')
            ).filter(Violation.company_name_normalized.isnot(None))
            
            if agency:
                query = query.filter(Violation.agency == agency)
            
            results = query.group_by(Violation.agency, Violation.company_name_normalized).all()
            
            for row in results:
                # Calculate years active
                years_active = None
                if row.first_violation_date and row.last_violation_date:
                    years_active = (row.last_violation_date.year - row.first_violation_date.year) + 1
                
                summary = ViolationSummaryByCompany(
                    agency=row.agency,
                    company_name_normalized=row.company_name_normalized,
                    violation_count=row.violation_count or 0,
                    total_penalties=row.total_penalties or 0.0,
                    avg_penalty=row.avg_penalty or 0.0,
                    first_violation_date=row.first_violation_date,
                    last_violation_date=row.last_violation_date,
                    years_active=years_active
                )
                session.add(summary)
            
            session.commit()
            logger.info(f"Refreshed company summary: {len(results)} records")
        except Exception as e:
            session.rollback()
            logger.error(f"Error refreshing company summary: {e}")
            raise
        finally:
            session.close()

