"""
Data validation and quality checks.
"""

import pandas as pd
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a data validation check."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)


class DataValidator:
    """Validates data quality and structure."""
    
    # Valid US state codes
    US_STATES = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
        'DC', 'PR', 'VI', 'AS', 'GU', 'MP'
    }
    
    def validate_dataframe(
        self, 
        df: pd.DataFrame, 
        required_columns: Optional[List[str]] = None,
        allow_empty: bool = False
    ) -> ValidationResult:
        """
        Validate DataFrame structure and basic quality.
        
        Args:
            df: DataFrame to validate
            required_columns: List of required column names
            allow_empty: If False, empty DataFrame is considered invalid
        
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(is_valid=True)
        
        # Check if DataFrame is empty
        if df.empty:
            if not allow_empty:
                result.add_error("DataFrame is empty")
            return result
        
        # Check required columns
        if required_columns:
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                result.add_error(f"Missing required columns: {', '.join(missing)}")
        
        # Basic statistics
        result.stats = {
            'row_count': len(df),
            'column_count': len(df.columns),
            'missing_values': df.isnull().sum().to_dict()
        }
        
        # Warn about high missing value rates
        for col, missing_count in result.stats['missing_values'].items():
            if missing_count > 0:
                missing_rate = missing_count / len(df) * 100
                if missing_rate > 50:
                    result.add_warning(f"Column '{col}' has {missing_rate:.1f}% missing values")
        
        return result
    
    def validate_year_range(
        self,
        df: pd.DataFrame,
        year_column: str,
        min_year: int = 1900,
        max_year: int = 2100
    ) -> ValidationResult:
        """Validate year values are in reasonable range."""
        result = ValidationResult(is_valid=True)
        
        if year_column not in df.columns:
            result.add_error(f"Column '{year_column}' not found")
            return result
        
        year_col = df[year_column]
        
        # Check for None/null values
        null_count = year_col.isnull().sum()
        if null_count > 0:
            result.add_warning(f"Found {null_count} null values in '{year_column}'")
        
        # Check valid years (not null and in range)
        valid_years = year_col.dropna()
        if len(valid_years) > 0:
            invalid = valid_years[(valid_years < min_year) | (valid_years > max_year)]
            if len(invalid) > 0:
                result.add_error(
                    f"Found {len(invalid)} years outside valid range ({min_year}-{max_year})"
                )
                result.stats['invalid_years'] = invalid.unique().tolist()
            
            result.stats['year_range'] = {
                'min': int(valid_years.min()),
                'max': int(valid_years.max()),
                'count': len(valid_years)
            }
        
        return result
    
    def validate_penalty_amounts(
        self,
        df: pd.DataFrame,
        penalty_column: str,
        min_value: float = 0.0,
        max_value: float = 10_000_000.0
    ) -> ValidationResult:
        """Validate penalty amounts are reasonable."""
        result = ValidationResult(is_valid=True)
        
        if penalty_column not in df.columns:
            result.add_error(f"Column '{penalty_column}' not found")
            return result
        
        penalty_col = df[penalty_column]
        
        # Check for negative values
        negative = penalty_col[penalty_col < 0]
        if len(negative) > 0:
            result.add_warning(f"Found {len(negative)} negative penalty amounts")
        
        # Check for values outside reasonable range
        valid_penalties = penalty_col.dropna()
        if len(valid_penalties) > 0:
            outliers = valid_penalties[
                (valid_penalties > max_value) | (valid_penalties < min_value)
            ]
            if len(outliers) > 0:
                result.add_warning(
                    f"Found {len(outliers)} penalty amounts outside typical range"
                )
            
            result.stats['penalty_stats'] = {
                'min': float(valid_penalties.min()),
                'max': float(valid_penalties.max()),
                'mean': float(valid_penalties.mean()),
                'median': float(valid_penalties.median())
            }
        
        return result
    
    def validate_state_codes(
        self,
        df: pd.DataFrame,
        state_column: str
    ) -> ValidationResult:
        """Validate state codes are valid US state abbreviations."""
        result = ValidationResult(is_valid=True)
        
        if state_column not in df.columns:
            result.add_error(f"Column '{state_column}' not found")
            return result
        
        state_col = df[state_column]
        unique_states = state_col.dropna().unique()
        
        invalid = [s for s in unique_states if str(s).upper() not in self.US_STATES]
        if invalid:
            result.add_warning(
                f"Found {len(invalid)} invalid state codes: {', '.join(map(str, invalid[:10]))}"
            )
            result.stats['invalid_states'] = invalid
        
        result.stats['valid_states'] = [s for s in unique_states if str(s).upper() in self.US_STATES]
        
        return result
    
    def validate_company_names(
        self,
        df: pd.DataFrame,
        name_column: str,
        max_length: int = 500
    ) -> ValidationResult:
        """Validate company names."""
        result = ValidationResult(is_valid=True)
        
        if name_column not in df.columns:
            result.add_error(f"Column '{name_column}' not found")
            return result
        
        name_col = df[name_column]
        
        # Check for empty strings
        empty = name_col[name_col == '']
        if len(empty) > 0:
            result.add_warning(f"Found {len(empty)} empty company names")
        
        # Check for very long names
        if name_col.dtype == 'object':
            long_names = name_col[name_col.str.len() > max_length]
            if len(long_names) > 0:
                result.add_warning(
                    f"Found {len(long_names)} company names longer than {max_length} characters"
                )
        
        # Check for None/null
        null_count = name_col.isnull().sum()
        if null_count > 0:
            result.add_warning(f"Found {null_count} null company names")
        
        return result
    
    def validate_comprehensive(
        self,
        df: pd.DataFrame,
        expected_columns: Optional[List[str]] = None
    ) -> ValidationResult:
        """Run comprehensive validation suite."""
        result = ValidationResult(is_valid=True)
        
        # Basic structure validation
        structure_result = self.validate_dataframe(df, required_columns=expected_columns)
        result.errors.extend(structure_result.errors)
        result.warnings.extend(structure_result.warnings)
        result.stats.update(structure_result.stats)
        
        # Column-specific validations if columns exist
        if 'year' in df.columns:
            year_result = self.validate_year_range(df, 'year')
            result.errors.extend(year_result.errors)
            result.warnings.extend(year_result.warnings)
            result.stats['year_validation'] = year_result.stats
        
        if 'current_penalty' in df.columns or 'penalty' in df.columns:
            penalty_col = 'current_penalty' if 'current_penalty' in df.columns else 'penalty'
            penalty_result = self.validate_penalty_amounts(df, penalty_col)
            result.warnings.extend(penalty_result.warnings)
            result.stats['penalty_validation'] = penalty_result.stats
        
        if 'site_state' in df.columns or 'state' in df.columns:
            state_col = 'site_state' if 'site_state' in df.columns else 'state'
            state_result = self.validate_state_codes(df, state_col)
            result.warnings.extend(state_result.warnings)
            result.stats['state_validation'] = state_result.stats
        
        if 'company_name' in df.columns or 'estab_name' in df.columns:
            name_col = 'company_name' if 'company_name' in df.columns else 'estab_name'
            name_result = self.validate_company_names(df, name_col)
            result.warnings.extend(name_result.warnings)
        
        if result.errors:
            result.is_valid = False
        
        return result

