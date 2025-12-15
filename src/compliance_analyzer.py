"""
Multi-Agency Compliance Analyzer
Provides cross-agency company compliance analysis and comparison.
"""

# Standard library imports
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# Third-party imports
import pandas as pd

# Local imports
from .agency_base import AgencyDataLoader, OSHADataLoader
from .database import get_db_manager, Violation
from .epa_loader import EPADataLoader, MSHADataLoader, FDADataLoader
from .fuzzy_matcher import CompanyNameMatcher
from .risk_scorer import RiskScorer
from .violation_impact import ViolationImpactAnalyzer

logger = logging.getLogger(__name__)


class ComplianceAnalyzer:
    """Analyzer for cross-agency compliance comparisons."""
    
    def __init__(
        self, 
        data_dir: Optional[Path] = None, 
        sample_size: Optional[int] = None,
        fuzzy_threshold: int = 75
    ):
        """
        Initialize analyzer with multiple agency loaders.
        
        Args:
            data_dir: Directory containing data files (defaults to project data directory)
            sample_size: Optional limit on number of rows to load (for testing)
            fuzzy_threshold: Minimum similarity score for fuzzy matching (0-100)
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        
        self.data_dir = data_dir
        self.sample_size = sample_size
        
        # Initialize fuzzy matcher, risk scorer, and impact analyzer
        self.fuzzy_matcher = CompanyNameMatcher(threshold=fuzzy_threshold)
        self.risk_scorer = RiskScorer()
        self.impact_analyzer = ViolationImpactAnalyzer()
        
        # Initialize agency loaders
        self.agencies: Dict[str, AgencyDataLoader] = {}
        
        # Load OSHA (always available)
        try:
            self.agencies["OSHA"] = OSHADataLoader(data_dir, fuzzy_threshold=fuzzy_threshold)
        except Exception as e:
            logger.warning(f"Could not load OSHA data: {e}")
        
        # Load other agencies (may not have data yet)
        try:
            self.agencies["EPA"] = EPADataLoader(data_dir, fuzzy_threshold=fuzzy_threshold)
        except Exception as e:
            logger.warning(f"Could not load EPA data: {e}")
        
        try:
            self.agencies["MSHA"] = MSHADataLoader(data_dir, fuzzy_threshold=fuzzy_threshold)
        except Exception as e:
            logger.warning(f"Could not load MSHA data: {e}")
        
        try:
            self.agencies["FDA"] = FDADataLoader(data_dir, fuzzy_threshold=fuzzy_threshold)
        except Exception as e:
            logger.warning(f"Could not load FDA data: {e}")
    
    def search_company(
        self, 
        company_name: str, 
        agencies: Optional[List[str]] = None, 
        use_db: bool = True,
        use_fuzzy: bool = True,
        fuzzy_threshold: Optional[int] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> pd.DataFrame:
        """
        Search for a company across all or specified agencies.
        
        Args:
            company_name: Company name to search for
            agencies: List of agency names to search (None = all agencies)
            use_db: If True, use database queries (faster); if False, use CSV loaders
        
        Returns:
            DataFrame with violations from all matching agencies
        """
        # Try database first if available
        if use_db:
            try:
                return self._search_company_db(
                    company_name, 
                    agencies,
                    use_fuzzy=use_fuzzy,
                    fuzzy_threshold=fuzzy_threshold
                )
            except Exception as e:
                logger.warning(f"Database search failed, falling back to CSV: {e}")
        
        # Fallback to CSV-based search
        if agencies is None:
            agencies = list(self.agencies.keys())
        
        all_results = []
        
        for agency_name in agencies:
            if agency_name not in self.agencies:
                continue
            
            try:
                loader = self.agencies[agency_name]
                results = loader.search_by_company(
                    company_name, 
                    nrows=self.sample_size,
                    use_fuzzy=use_fuzzy,
                    fuzzy_threshold=fuzzy_threshold
                )
                
                if not results.empty:
                    # Ensure results are prepared for comparison
                    if 'agency' not in results.columns:
                        results = loader.prepare_for_comparison(results)
                    all_results.append(results)
            except Exception as e:
                logger.error(f"Error searching {agency_name}: {e}")
                continue
        
        if not all_results:
            return pd.DataFrame()
        
        combined = pd.concat(all_results, ignore_index=True)
        
        # Sort by similarity score if available
        if 'similarity_score' in combined.columns:
            combined = combined.sort_values('similarity_score', ascending=False)
        
        # Apply pagination
        combined = combined.iloc[offset:offset + limit]
        
        return combined
    
    def _search_company_db(
        self, 
        company_name: str, 
        agencies: Optional[List[str]] = None,
        use_fuzzy: bool = True,
        fuzzy_threshold: Optional[int] = None
    ) -> pd.DataFrame:
        """Search company using database queries with optional fuzzy matching."""
        from sqlalchemy import func
        
        db = get_db_manager(data_dir=self.data_dir)
        session = db.get_session()
        
        try:
            # Use the fuzzy_matcher to normalize the company name
            normalized_name = self.fuzzy_matcher.normalize_company_name(company_name)
            
            query = session.query(Violation)
            
            # Basic filtering by normalized name (for database query)
            # Use case-insensitive matching compatible with both SQLite and PostgreSQL
            company_name_lower = company_name.lower()
            query = query.filter(
                (Violation.company_name_normalized.contains(normalized_name)) |
                (func.lower(Violation.company_name).like(f"%{company_name_lower}%"))
            )
            
            # Filter by agencies
            if agencies:
                query = query.filter(Violation.agency.in_(agencies))
            
            # Get results from database
            df = pd.read_sql(query.statement, session.bind)
            
            # Apply fuzzy matching if requested
            if use_fuzzy and not df.empty:
                threshold = fuzzy_threshold or self.fuzzy_matcher.threshold
                
                # Get unique company names from results
                company_cols = ['company_name', 'estab_name', 'facility_name', 'mine_name', 'firm_name']
                company_col = None
                for col in company_cols:
                    if col in df.columns:
                        company_col = col
                        break
                
                if company_col:
                    # Calculate similarity scores
                    df['similarity_score'] = df[company_col].apply(
                        lambda x: self.fuzzy_matcher.calculate_similarity(company_name, x) if pd.notna(x) else 0
                    )
                    
                    # Filter by threshold
                    df = df[df['similarity_score'] >= threshold]
                    
                    # Sort by similarity
                    df = df.sort_values('similarity_score', ascending=False)
            
            # Apply sample_size limit if set
            if self.sample_size:
                df = df.head(self.sample_size)
            
            return df
        finally:
            session.close()
    
    def compare_company_across_agencies(
        self, 
        company_name: str,
        agencies: Optional[List[str]] = None,
        include_risk_score: bool = True,
        use_fuzzy: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive compliance summary for a company across agencies.
        
        Args:
            company_name: Company name to analyze
            agencies: List of agencies to include (None = all)
            include_risk_score: If True, calculate risk score (default: True)
            use_fuzzy: If True, use fuzzy matching (default: True)
        
        Returns:
            Dictionary with summary statistics by agency and risk score
        """
        violations_df = self.search_company(company_name, agencies, use_fuzzy=use_fuzzy)
        
        if violations_df.empty:
            return {
                "company_name": company_name,
                "total_violations": 0,
                "agencies": {},
                "total_penalties": 0
            }
        
        summary = {
            "company_name": company_name,
            "total_violations": len(violations_df),
            "agencies": {},
            "total_penalties": 0,
            "violations_by_agency": {}
        }
        
        # Summarize by agency
        if "agency" in violations_df.columns:
            for agency in violations_df["agency"].unique():
                agency_df = violations_df[violations_df["agency"] == agency]
                
                agency_summary = {
                    "violation_count": len(agency_df),
                    "penalties": {}
                }
                
                # Calculate penalties if available
                penalty_cols = ["current_penalty", "penalty_amount", "total_penalty"]
                penalty_col = None
                for col in penalty_cols:
                    if col in agency_df.columns:
                        penalty_col = col
                        break
                
                if penalty_col:
                    agency_summary["penalties"] = {
                        "total": float(agency_df[penalty_col].sum()) if pd.api.types.is_numeric_dtype(agency_df[penalty_col]) else 0,
                        "average": float(agency_df[penalty_col].mean()) if pd.api.types.is_numeric_dtype(agency_df[penalty_col]) else 0,
                        "max": float(agency_df[penalty_col].max()) if pd.api.types.is_numeric_dtype(agency_df[penalty_col]) else 0
                    }
                    if "total" in agency_summary["penalties"]:
                        summary["total_penalties"] += agency_summary["penalties"]["total"]
                
                # Add violation types if available
                if "viol_type" in agency_df.columns:
                    agency_summary["violation_types"] = agency_df["viol_type"].value_counts().to_dict()
                
                summary["agencies"][agency] = agency_summary
                summary["violations_by_agency"][agency] = agency_df
        
        # Calculate risk score if requested
        if include_risk_score and not violations_df.empty:
            risk_data = self.risk_scorer.calculate_composite_score(violations_df)
            summary['risk_score'] = risk_data
        
        return summary
    
    def get_company_risk_score(
        self,
        company_name: str,
        agencies: Optional[List[str]] = None,
        use_fuzzy: bool = True
    ) -> Dict[str, Any]:
        """
        Get detailed risk score for a company.
        
        Returns:
            Dictionary with risk score, components, and factors
        """
        violations_df = self.search_company(company_name, agencies, use_fuzzy=use_fuzzy)
        return self.risk_scorer.calculate_composite_score(violations_df)
    
    def analyze_violation_impact(
        self,
        company_name: str,
        agencies: Optional[List[str]] = None,
        use_fuzzy: bool = True,
        violation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze whether violations increased or reduced subsequent violations.
        
        Args:
            company_name: Company name to analyze
            agencies: List of agencies to include
            use_fuzzy: Use fuzzy matching for company search
            violation_id: Specific violation ID to analyze (None = automatic selection)
        
        Returns:
            Dictionary with impact analysis results
        """
        violations_df = self.search_company(company_name, agencies, use_fuzzy=use_fuzzy)
        
        if violations_df.empty:
            return {'error': 'No violations found for company'}
        
        # Determine date column
        date_col = 'violation_date'
        if date_col not in violations_df.columns:
            # Try alternatives
            for col in ['open_date', 'year', 'violation_date']:
                if col in violations_df.columns:
                    date_col = col
                    break
        
        # Analyze impact
        if violation_id:
            impact_result = self.impact_analyzer.calculate_violation_impact(
                violations_df,
                violation_id=violation_id,
                date_col=date_col
            )
        else:
            # Analyze overall patterns
            impact_result = self.impact_analyzer.analyze_company_violation_patterns(
                violations_df,
                date_col=date_col
            )
        
        return {
            'company_name': company_name,
            'total_violations': len(violations_df),
            'impact_analysis': impact_result
        }
    
    def get_companies_with_cross_agency_violations(
        self,
        min_violations: int = 1,
        agencies: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Find companies that have violations across multiple agencies.
        
        Args:
            min_violations: Minimum number of violations per agency to include
            agencies: List of agencies to check (None = all)
        
        Returns:
            DataFrame with companies and their violation counts by agency
        """
        if agencies is None:
            agencies = list(self.agencies.keys())
        
        # Get all violations from all agencies
        all_violations = []
        
        for agency_name in agencies:
            if agency_name not in self.agencies:
                continue
            
            try:
                loader = self.agencies[agency_name]
                violations = loader.load_violations(nrows=self.sample_size)
                
                if not violations.empty:
                    violations = loader.prepare_for_comparison(violations)
                    all_violations.append(violations)
            except Exception as e:
                logger.error(f"Error loading {agency_name} data: {e}")
                continue
        
        if not all_violations:
            return pd.DataFrame()
        
        combined = pd.concat(all_violations, ignore_index=True)
        
        if combined.empty or "company_name_normalized" not in combined.columns:
            return pd.DataFrame()
        
        # Group by normalized company name and agency
        cross_agency = combined.groupby(["company_name_normalized", "agency"]).size().reset_index(name="violation_count")
        
        # Filter by minimum violations
        cross_agency = cross_agency[cross_agency["violation_count"] >= min_violations]
        
        # Pivot to show agencies as columns
        pivot = cross_agency.pivot(
            index="company_name_normalized",
            columns="agency",
            values="violation_count"
        ).fillna(0)
        
        # Only keep companies with violations in multiple agencies
        pivot = pivot[(pivot > 0).sum(axis=1) > 1]
        
        return pivot.reset_index()
    
    def get_available_agencies(self) -> List[str]:
        """Return list of available agencies with data."""
        available = []
        
        for agency_name, loader in self.agencies.items():
            try:
                violations = loader.load_violations(nrows=1)
                if not violations.empty:
                    available.append(agency_name)
            except:
                pass
        
        return available

