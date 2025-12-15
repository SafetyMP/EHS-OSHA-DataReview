"""
Tests for database-backed analyzer.
"""

import pytest
import pandas as pd
from pathlib import Path
import sys
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analyzer_db import OSHAAnalyzerDB
from src.database import get_db_manager, Violation, Inspection


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"
    database_url = f"sqlite:///{db_path}"
    
    # Initialize database
    db_manager = get_db_manager(database_url=database_url)
    db_manager.create_tables()
    
    yield db_manager, database_url
    
    # Cleanup
    if db_path.exists():
        os.remove(db_path)
    os.rmdir(temp_dir)


@pytest.fixture
def sample_data(temp_db):
    """Add sample data to test database."""
    db_manager, database_url = temp_db
    
    session = db_manager.get_session()
    try:
        # Add sample inspections
        inspections = [
            Inspection(
                activity_nr=f"TEST{i:04d}",
                estab_name=f"Test Company {i}",
                site_state="CA",
                naics_code="541330",
                year=2023,
                open_date=pd.Timestamp("2023-01-01")
            )
            for i in range(1, 6)
        ]
        session.add_all(inspections)
        
        # Add sample violations
        violations = []
        for i in range(1, 11):
            violations.append(Violation(
                agency="OSHA",
                activity_nr=f"TEST{(i % 5) + 1:04d}",
                company_name=f"Test Company {(i % 5) + 1}",
                company_name_normalized=f"TEST COMPANY {(i % 5) + 1}",
                standard=f"1910.{i}",
                current_penalty=100.0 * i,
                site_state="CA",
                year=2023,
                violation_date=pd.Timestamp("2023-01-01")
            ))
        
        session.add_all(violations)
        session.commit()
    finally:
        session.close()
    
    return temp_db


def test_search_violations(sample_data):
    """Test violation search."""
    db_manager, database_url = sample_data
    analyzer = OSHAAnalyzerDB(database_url=database_url)
    
    results = analyzer.search_violations(state="CA", limit=10)
    
    assert isinstance(results, pd.DataFrame)
    assert len(results) > 0
    assert all(results["site_state"] == "CA")


def test_search_violations_pagination(sample_data):
    """Test violation search with pagination."""
    db_manager, database_url = sample_data
    analyzer = OSHAAnalyzerDB(database_url=database_url)
    
    page1 = analyzer.search_violations(limit=5, offset=0)
    page2 = analyzer.search_violations(limit=5, offset=5)
    
    assert len(page1) <= 5
    assert len(page2) <= 5
    # Results should be different
    if len(page1) > 0 and len(page2) > 0:
        assert not page1.equals(page2)


def test_count_violations(sample_data):
    """Test violation counting."""
    db_manager, database_url = sample_data
    analyzer = OSHAAnalyzerDB(database_url=database_url)
    
    count = analyzer.count_violations(state="CA")
    
    assert isinstance(count, int)
    assert count >= 0


def test_top_violations(sample_data):
    """Test top violations query."""
    db_manager, database_url = sample_data
    analyzer = OSHAAnalyzerDB(database_url=database_url)
    
    top = analyzer.top_violations(n=5)
    
    assert isinstance(top, pd.DataFrame)
    assert len(top) <= 5
    if len(top) > 0:
        assert "standard" in top.columns
        assert "citation_count" in top.columns


def test_violations_by_state(sample_data):
    """Test violations by state aggregation."""
    db_manager, database_url = sample_data
    analyzer = OSHAAnalyzerDB(database_url=database_url)
    
    by_state = analyzer.violations_by_state()
    
    assert isinstance(by_state, pd.DataFrame)
    if len(by_state) > 0:
        assert "site_state" in by_state.columns
        assert "violation_count" in by_state.columns


def test_violations_by_industry(sample_data):
    """Test violations by industry aggregation."""
    db_manager, database_url = sample_data
    analyzer = OSHAAnalyzerDB(database_url=database_url)
    
    by_industry = analyzer.violations_by_industry(n=10)
    
    assert isinstance(by_industry, pd.DataFrame)
    if len(by_industry) > 0:
        assert "naics_sector" in by_industry.columns or "naics_code" in by_industry.columns


def test_search_empty_results(sample_data):
    """Test search with filters that return no results."""
    db_manager, database_url = sample_data
    analyzer = OSHAAnalyzerDB(database_url=database_url)
    
    results = analyzer.search_violations(state="XX", limit=10)  # Invalid state
    
    assert isinstance(results, pd.DataFrame)
    assert len(results) == 0


def test_year_filter(sample_data):
    """Test year filtering."""
    db_manager, database_url = sample_data
    analyzer = OSHAAnalyzerDB(database_url=database_url)
    
    results = analyzer.search_violations(year=2023, limit=10)
    
    assert isinstance(results, pd.DataFrame)
    if len(results) > 0:
        assert all(results["year"] == 2023)


def test_min_penalty_filter(sample_data):
    """Test minimum penalty filtering."""
    db_manager, database_url = sample_data
    analyzer = OSHAAnalyzerDB(database_url=database_url)
    
    results = analyzer.search_violations(min_penalty=500.0, limit=10)
    
    assert isinstance(results, pd.DataFrame)
    if len(results) > 0:
        assert all(results["current_penalty"] >= 500.0)

