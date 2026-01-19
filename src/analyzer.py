"""
OSHA Analyzer
Analysis and visualization functions for OSHA enforcement data.
"""

import pandas as pd
from typing import Dict, Any, Optional

from .data_loader import load_inspections, load_violations, load_accidents


class OSHAAnalyzer:
    """Main analyzer class for OSHA enforcement data."""
    
    def __init__(self, sample_size: int = None):
        """Initialize analyzer and load data."""
        try:
            self.inspections = load_inspections(nrows=sample_size)
            self.violations = load_violations(nrows=sample_size)
            self.accidents = load_accidents(nrows=sample_size)
        except Exception as e:
            raise RuntimeError(f"Failed to load OSHA data: {e}") from e
        
        # Merge violations with inspection info
        if "activity_nr" in self.violations.columns and "activity_nr" in self.inspections.columns:
            inspection_cols = ["activity_nr", "estab_name", "site_state", "naics_code", "open_date", "year"]
            available_cols = [c for c in inspection_cols if c in self.inspections.columns]
            self.violations = self.violations.merge(
                self.inspections[available_cols],
                on="activity_nr",
                how="left"
            )
    
    def search_violations(
        self,
        state: str = None,
        naics_prefix: str = None,
        year: int = None,
        keyword: str = None,
        min_penalty: float = None,
        limit: int = 100,
        offset: int = 0
    ) -> pd.DataFrame:
        """Search violations with filters."""
        if self.violations.empty:
            return pd.DataFrame()
        
        df = self.violations.copy()
        
        if state and "site_state" in df.columns:
            df = df[df["site_state"] == state.upper()]
        
        if naics_prefix and "naics_code" in df.columns:
            df["naics_str"] = df["naics_code"].astype(str)
            df = df[df["naics_str"].str.startswith(naics_prefix)]
            df = df.drop(columns=["naics_str"])
        
        if year and "year" in df.columns:
            df = df[df["year"] == year]
        
        if keyword and "standard" in df.columns:
            df = df[df["standard"].str.contains(keyword, case=False, na=False)]
        
        if min_penalty and "current_penalty" in df.columns:
            df = df[df["current_penalty"] >= min_penalty]
        
        # Apply pagination
        return df.iloc[offset:offset + limit]
    
    def top_violations(self, n: int = 10, year: int = None) -> pd.DataFrame:
        """Get most frequently cited OSHA standards."""
        if self.violations.empty:
            return pd.DataFrame()
        
        df = self.violations.copy()
        
        if year and "year" in df.columns:
            df = df[df["year"] == year]
        
        if "standard" not in df.columns or df.empty:
            return pd.DataFrame()
        
        counts = df["standard"].value_counts().head(n).reset_index()
        counts.columns = ["standard", "citation_count"]
        
        # Add average penalty
        if "current_penalty" in df.columns:
            avg_penalties = df.groupby("standard")["current_penalty"].mean()
            counts["avg_penalty"] = counts["standard"].map(avg_penalties).round(2)
        
        return counts
    
    def violations_by_state(self, year: int = None) -> pd.DataFrame:
        """Get violation counts by state."""
        if self.violations.empty:
            return pd.DataFrame()
        
        df = self.violations.copy()
        
        if year and "year" in df.columns:
            df = df[df["year"] == year]
        
        if "site_state" not in df.columns or df.empty:
            return pd.DataFrame()
        
        counts = df["site_state"].value_counts().reset_index()
        counts.columns = ["state", "violation_count"]
        
        if "current_penalty" in df.columns:
            total_penalties = df.groupby("site_state")["current_penalty"].sum()
            counts["total_penalties"] = counts["state"].map(total_penalties).round(2)
        
        return counts
    
    def violations_by_industry(self, year: int = None, n: int = 15) -> pd.DataFrame:
        """Get violation counts by NAICS industry code."""
        if self.violations.empty:
            return pd.DataFrame()
        
        df = self.violations.copy()
        
        if year and "year" in df.columns:
            df = df[df["year"] == year]
        
        if "naics_code" not in df.columns or df.empty:
            return pd.DataFrame()
        
        # Group by 2-digit NAICS (sector level)
        df["naics_sector"] = df["naics_code"].astype(str).str[:2]
        
        counts = df["naics_sector"].value_counts().head(n).reset_index()
        counts.columns = ["naics_sector", "violation_count"]
        
        # Add sector names
        sector_names = {
            "11": "Agriculture", "21": "Mining", "22": "Utilities",
            "23": "Construction", "31": "Manufacturing", "32": "Manufacturing",
            "33": "Manufacturing", "42": "Wholesale Trade", "44": "Retail Trade",
            "45": "Retail Trade", "48": "Transportation", "49": "Warehousing",
            "51": "Information", "52": "Finance", "53": "Real Estate",
            "54": "Professional Services", "55": "Management", "56": "Admin Services",
            "61": "Education", "62": "Healthcare", "71": "Arts/Entertainment",
            "72": "Accommodation/Food", "81": "Other Services", "92": "Public Admin"
        }
        counts["sector_name"] = counts["naics_sector"].map(sector_names)
        
        if "current_penalty" in df.columns:
            avg_penalties = df.groupby("naics_sector")["current_penalty"].mean()
            counts["avg_penalty"] = counts["naics_sector"].map(avg_penalties).round(2)
        
        return counts
    
    def penalty_summary(self, group_by: str = "viol_type") -> pd.DataFrame:
        """Summarize penalties by grouping variable."""
        if self.violations.empty:
            return pd.DataFrame()
        
        df = self.violations.copy()
        
        if group_by not in df.columns or "current_penalty" not in df.columns or df.empty:
            return pd.DataFrame()
        
        summary = df.groupby(group_by).agg(
            count=("current_penalty", "count"),
            total_penalty=("current_penalty", "sum"),
            avg_penalty=("current_penalty", "mean"),
            max_penalty=("current_penalty", "max")
        ).round(2).reset_index()
        
        return summary.sort_values("total_penalty", ascending=False)
    
    def trend_analysis(self, metric: str = "inspections", year: Optional[int] = None, state: Optional[str] = None) -> pd.DataFrame:
        """Analyze trends over time.
        
        Args:
            metric: Type of analysis ("violations", "inspections", or "penalties")
            year: Optional year filter (applied as exact match)
            state: Optional state filter (applied to site_state)
        """
        if metric == "inspections":
            if self.inspections.empty:
                return pd.DataFrame()
            df = self.inspections.copy()
            if "year" not in df.columns:
                return pd.DataFrame()
            # Apply filters
            if state and "site_state" in df.columns:
                df = df[df["site_state"] == state]
            if year:
                df = df[df["year"] == year]
            counts = df["year"].value_counts().sort_index().reset_index()
            counts.columns = ["year", "count"]
        
        elif metric == "violations":
            if self.violations.empty:
                return pd.DataFrame()
            df = self.violations.copy()
            if "year" not in df.columns:
                return pd.DataFrame()
            # Apply filters
            if state and "site_state" in df.columns:
                df = df[df["site_state"] == state]
            if year:
                df = df[df["year"] == year]
            counts = df["year"].value_counts().sort_index().reset_index()
            counts.columns = ["year", "count"]
        
        elif metric == "penalties":
            if self.violations.empty:
                return pd.DataFrame()
            df = self.violations.copy()
            if "year" not in df.columns or "current_penalty" not in df.columns:
                return pd.DataFrame()
            # Apply filters
            if state and "site_state" in df.columns:
                df = df[df["site_state"] == state]
            if year:
                df = df[df["year"] == year]
            counts = df.groupby("year")["current_penalty"].sum().reset_index()
            counts.columns = ["year", "total_penalty"]
        
        else:
            return pd.DataFrame()
        
        return counts
    
    def industry_benchmark(self, naics_code: str) -> Dict[str, Any]:
        """Compare a specific industry to national averages."""
        if self.violations.empty:
            return {}
        
        df = self.violations.copy()
        
        if "naics_code" not in df.columns:
            return {}
        
        # Filter to target industry
        df["naics_str"] = df["naics_code"].astype(str)
        industry_df = df[df["naics_str"].str.startswith(naics_code[:2])]
        
        benchmark = {
            "naics_code": naics_code,
            "industry_violation_count": len(industry_df),
            "national_violation_count": len(df),
            "industry_pct_of_total": round(len(industry_df) / len(df) * 100, 2) if len(df) > 0 else 0
        }
        
        if "current_penalty" in df.columns:
            benchmark["industry_avg_penalty"] = round(industry_df["current_penalty"].mean(), 2)
            benchmark["national_avg_penalty"] = round(df["current_penalty"].mean(), 2)
        
        return benchmark


# Standard OSHA violation descriptions
COMMON_STANDARDS = {
    "1910.134": "Respiratory Protection",
    "1910.147": "Control of Hazardous Energy (Lockout/Tagout)",
    "1926.501": "Fall Protection",
    "1910.178": "Powered Industrial Trucks (Forklifts)",
    "1910.1200": "Hazard Communication",
    "1926.1053": "Ladders",
    "1910.305": "Electrical - Wiring Methods",
    "1926.451": "Scaffolding",
    "1910.212": "Machine Guarding",
    "1910.303": "Electrical - General Requirements"
}


def get_standard_description(standard: str) -> str:
    """Look up description for an OSHA standard number."""
    # Try exact match first
    if standard in COMMON_STANDARDS:
        return COMMON_STANDARDS[standard]
    
    # Try prefix match
    for key, desc in COMMON_STANDARDS.items():
        if standard.startswith(key):
            return desc
    
    return "Unknown Standard"
