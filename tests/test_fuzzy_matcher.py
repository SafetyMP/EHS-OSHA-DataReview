"""
Tests for fuzzy matching functionality.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fuzzy_matcher import CompanyNameMatcher


@pytest.fixture
def matcher():
    """Create a matcher instance."""
    return CompanyNameMatcher()


def test_exact_match(matcher):
    """Test exact company name match."""
    result = matcher.find_best_match("AMAZON", ["AMAZON", "APPLE", "GOOGLE"])
    assert result[0] == "AMAZON"
    assert result[1] >= 90  # High similarity


def test_case_insensitive(matcher):
    """Test case-insensitive matching."""
    result = matcher.find_best_match("amazon", ["AMAZON", "APPLE"])
    assert result[0] == "AMAZON"
    assert result[1] >= 90


def test_partial_match(matcher):
    """Test partial string matching."""
    result = matcher.find_best_match("Amazon Web Services", ["AMAZON", "AMAZON WEB SERVICES"])
    assert result[0] == "AMAZON WEB SERVICES"
    assert result[1] >= 75


def test_no_match(matcher):
    """Test when no good match exists."""
    result = matcher.find_best_match("XYZ Company", ["AMAZON", "APPLE"], threshold=80)
    assert result is None or result[1] < 80


def test_normalization(matcher):
    """Test company name normalization."""
    normalized = matcher.normalize_company_name("Amazon.com, Inc.")
    assert "INC" in normalized
    assert "." not in normalized
    assert "," not in normalized


def test_fuzzy_algorithms(matcher):
    """Test different fuzzy matching algorithms."""
    company = "AMAZON SERVICES"
    candidates = ["AMAZON", "AMAZON WEB SERVICES", "APPLE SERVICES"]
    
    # Test each algorithm
    ratio_score = matcher.match_ratio(company, candidates[0])
    partial_score = matcher.match_partial_ratio(company, candidates[1])
    token_sort_score = matcher.match_token_sort_ratio(company, candidates[1])
    
    assert ratio_score >= 0
    assert partial_score >= 0
    assert token_sort_score >= 0
    assert all(score <= 100 for score in [ratio_score, partial_score, token_sort_score])

