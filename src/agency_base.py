"""
Base classes for agency data loaders.
Provides a common interface for loading and processing data from different regulatory agencies.
"""

import pandas as pd
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path

from .fuzzy_matcher import CompanyNameMatcher


class AgencyDataLoader(ABC):
    """Base class for agency data loaders."""
    
    def __init__(self, data_dir: Path, fuzzy_threshold: int = 75):
        """
        Initialize with data directory path.
        
        Args:
            data_dir: Directory for data files
            fuzzy_threshold: Minimum similarity score for fuzzy matching (0-100)
        """
        self.data_dir = data_dir
        self.agency_name = self.get_agency_name()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.fuzzy_matcher = CompanyNameMatcher(threshold=fuzzy_threshold)
    
    @abstractmethod
    def get_agency_name(self) -> str:
        """Return the name of the agency (e.g., 'OSHA', 'EPA')."""
        pass
    
    @abstractmethod
    def load_violations(self, nrows: Optional[int] = None) -> pd.DataFrame:
        """Load violation/enforcement data from the agency."""
        pass
    
    @abstractmethod
    def get_company_name_column(self) -> str:
        """Return the column name that contains company/facility names."""
        pass
    
    def normalize_company_name(self, name: str) -> str:
        """Normalize company name for matching across agencies."""
        return self.fuzzy_matcher.normalize_company_name(name)
    
    def add_agency_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add agency identifier column to dataframe."""
        if not df.empty:
            df = df.copy()
            df["agency"] = self.agency_name
        return df
    
    def prepare_for_comparison(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare dataframe for cross-agency comparison by adding normalized company names."""
        if df.empty:
            return df
        
        df = df.copy()
        company_col = self.get_company_name_column()
        
        if company_col in df.columns:
            df["company_name_normalized"] = df[company_col].apply(self.normalize_company_name)
        
        return self.add_agency_column(df)
    
    def search_by_company(
        self, 
        company_name: str, 
        nrows: Optional[int] = None,
        use_fuzzy: bool = True,
        fuzzy_threshold: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Search for violations by company name with fuzzy matching support.
        
        Args:
            company_name: Company name to search for
            nrows: Limit number of rows to load
            use_fuzzy: If True, use fuzzy matching (default: True)
            fuzzy_threshold: Minimum similarity score for fuzzy matching
        
        Returns:
            DataFrame with matched violations, sorted by similarity score if fuzzy matching used
        """
        violations = self.load_violations(nrows=nrows)
        
        if violations.empty:
            return pd.DataFrame()
        
        company_col = self.get_company_name_column()
        if company_col not in violations.columns:
            return pd.DataFrame()
        
        violations = self.prepare_for_comparison(violations)
        
        if use_fuzzy:
            # Use fuzzy matching
            threshold = fuzzy_threshold or self.fuzzy_matcher.threshold
            matched_df = self.fuzzy_matcher.match_dataframe(
                company_name,
                violations,
                company_col=company_col,
                threshold=threshold,
                limit=nrows or 1000
            )
            
            if not matched_df.empty:
                # Sort by similarity score
                matched_df = matched_df.sort_values('similarity_score', ascending=False)
            
            return matched_df
        else:
            # Use exact/substring matching (original behavior)
            normalized_search = self.normalize_company_name(company_name)
            mask = (
                violations[company_col].str.upper().str.contains(company_name.upper(), case=False, na=False) |
                violations["company_name_normalized"].str.contains(normalized_search, case=False, na=False)
            )
            return violations[mask]


class OSHADataLoader(AgencyDataLoader):
    """OSHA-specific data loader."""
    
    def get_agency_name(self) -> str:
        return "OSHA"
    
    def get_company_name_column(self) -> str:
        return "estab_name"
    
    def load_violations(self, nrows: Optional[int] = None) -> pd.DataFrame:
        """Load OSHA violations with inspection data merged."""
        from .data_loader import load_inspections, load_violations
        
        violations = load_violations(nrows=nrows)
        inspections = load_inspections(nrows=nrows)
        
        if violations.empty:
            return pd.DataFrame()
        
        # Merge with inspection data to get company names
        if "activity_nr" in violations.columns and "activity_nr" in inspections.columns:
            inspection_cols = ["activity_nr", "estab_name", "site_state", "naics_code", "open_date", "year"]
            available_cols = [c for c in inspection_cols if c in inspections.columns]
            violations = violations.merge(
                inspections[available_cols],
                on="activity_nr",
                how="left"
            )
        
        return violations

