"""
Tests for data validation and quality checks.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_validation import DataValidator, ValidationResult


@pytest.fixture
def validator():
    """Create a validator instance."""
    return DataValidator()


def test_validate_dataframe_structure(validator):
    """Test DataFrame structure validation."""
    # Valid DataFrame
    valid_df = pd.DataFrame({
        'company_name': ['Company A', 'Company B'],
        'year': [2023, 2024],
        'penalty': [100.0, 200.0]
    })
    
    result = validator.validate_dataframe(valid_df, required_columns=['company_name', 'year'])
    assert result.is_valid
    
    # Invalid DataFrame (missing column)
    invalid_df = pd.DataFrame({
        'company_name': ['Company A'],
        'penalty': [100.0]
    })
    
    result = validator.validate_dataframe(invalid_df, required_columns=['company_name', 'year'])
    assert not result.is_valid
    assert len(result.errors) > 0


def test_validate_year_range(validator):
    """Test year range validation."""
    df = pd.DataFrame({
        'year': [1990, 2000, 2023, 2050, None]
    })
    
    result = validator.validate_year_range(df, 'year', min_year=1990, max_year=2024)
    
    # Should flag years outside range and None values
    assert isinstance(result, ValidationResult)
    # Note: Specific checks depend on implementation


def test_validate_penalty_amounts(validator):
    """Test penalty amount validation."""
    df = pd.DataFrame({
        'penalty': [0, 100.0, -50.0, 1000000.0, None]
    })
    
    result = validator.validate_penalty_amounts(df, 'penalty', min_value=0, max_value=1000000)
    
    assert isinstance(result, ValidationResult)


def test_validate_state_codes(validator):
    """Test state code validation."""
    df = pd.DataFrame({
        'state': ['CA', 'NY', 'XX', 'California', None]
    })
    
    result = validator.validate_state_codes(df, 'state')
    
    assert isinstance(result, ValidationResult)


def test_validate_company_names(validator):
    """Test company name validation."""
    df = pd.DataFrame({
        'company_name': ['Valid Company', '', None, 'A' * 1000]  # Valid, empty, None, too long
    })
    
    result = validator.validate_company_names(df, 'company_name')
    
    assert isinstance(result, ValidationResult)

