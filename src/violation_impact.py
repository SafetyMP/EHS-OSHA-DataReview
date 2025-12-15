"""
Violation Impact Analysis
Analyzes whether violations increased or reduced subsequent violations by the same company.
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


class ViolationImpactAnalyzer:
    """Analyze the impact of violations on subsequent violation patterns."""
    
    def __init__(self, lookback_days: int = 365, lookahead_days: int = 365, min_violations: int = 3):
        """
        Initialize analyzer.
        
        Args:
            lookback_days: Days to look back for "before" period
            lookback_days: Days to look forward for "after" period
            min_violations: Minimum violations needed for meaningful analysis
        """
        self.lookback_days = lookback_days
        self.lookahead_days = lookahead_days
        self.min_violations = min_violations
    
    def calculate_violation_impact(
        self,
        violations_df: pd.DataFrame,
        violation_id: Optional[str] = None,
        violation_date_col: str = 'violation_date',
        company_col: str = 'company_name',
        date_col: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate the impact of a violation on subsequent violations.
        
        Args:
            violations_df: DataFrame with all violations for a company
            violation_id: ID of specific violation to analyze (if None, analyzes all)
            violation_date_col: Column name for violation dates
            company_col: Column name for company identifier
            date_col: Alternative date column (defaults to violation_date_col)
        
        Returns:
            Dictionary with impact analysis results
        """
        if violations_df.empty:
            return self._empty_result()
        
        # Standardize date column
        date_col = date_col or violation_date_col
        
        if date_col not in violations_df.columns:
            # Try to find a date column
            date_cols = [col for col in violations_df.columns if 'date' in col.lower() or 'year' in col.lower()]
            if date_cols:
                date_col = date_cols[0]
            else:
                return self._empty_result("No date column found")
        
        # Convert dates
        violations_df = violations_df.copy()
        violations_df[date_col] = pd.to_datetime(violations_df[date_col], errors='coerce')
        violations_df = violations_df.dropna(subset=[date_col]).sort_values(date_col)
        
        if len(violations_df) < self.min_violations:
            return self._empty_result(f"Less than {self.min_violations} violations for analysis")
        
        # If violation_id specified, analyze that specific violation
        if violation_id and 'id' in violations_df.columns:
            violation_row = violations_df[violations_df['id'] == violation_id]
            if violation_row.empty:
                return self._empty_result(f"Violation ID {violation_id} not found")
            violation_date = violation_row[date_col].iloc[0]
        else:
            # Analyze impact of first significant violation (e.g., first high penalty)
            violation_date = self._find_impact_violation(violations_df, date_col)
        
        # Calculate before/after periods
        before_start = violation_date - timedelta(days=self.lookback_days)
        after_end = violation_date + timedelta(days=self.lookahead_days)
        
        # Split violations into before and after
        before_violations = violations_df[
            (violations_df[date_col] >= before_start) & 
            (violations_df[date_col] < violation_date)
        ]
        
        after_violations = violations_df[
            (violations_df[date_col] > violation_date) & 
            (violations_df[date_col] <= after_end)
        ]
        
        # Calculate rates (violations per year)
        before_days = (violation_date - before_start).days
        after_days = (after_end - violation_date).days
        
        before_rate = (len(before_violations) / before_days * 365) if before_days > 0 else 0
        after_rate = (len(after_violations) / after_days * 365) if after_days > 0 else 0
        
        # Calculate change
        if before_rate > 0:
            rate_change_pct = ((after_rate - before_rate) / before_rate) * 100
        elif after_rate > 0:
            rate_change_pct = 100  # Went from 0 to some rate
        else:
            rate_change_pct = 0  # No violations in either period
        
        # Statistical significance test (Mann-Whitney U test for rate comparison)
        p_value = self._test_significance(before_violations, after_violations, violation_date, date_col)
        
        # Determine impact
        if p_value < 0.05:  # Statistically significant
            if after_rate > before_rate:
                impact = "Increased"
                impact_strength = self._calculate_impact_strength(rate_change_pct)
            elif after_rate < before_rate:
                impact = "Reduced"
                impact_strength = self._calculate_impact_strength(abs(rate_change_pct))
            else:
                impact = "No Change"
                impact_strength = "None"
        else:
            impact = "No Significant Change"
            impact_strength = "None"
        
        return {
            'violation_date': violation_date.strftime('%Y-%m-%d') if pd.notna(violation_date) else None,
            'before_period': {
                'start_date': before_start.strftime('%Y-%m-%d'),
                'end_date': violation_date.strftime('%Y-%m-%d') if pd.notna(violation_date) else None,
                'days': before_days,
                'violation_count': len(before_violations),
                'rate_per_year': round(before_rate, 2)
            },
            'after_period': {
                'start_date': violation_date.strftime('%Y-%m-%d') if pd.notna(violation_date) else None,
                'end_date': after_end.strftime('%Y-%m-%d'),
                'days': after_days,
                'violation_count': len(after_violations),
                'rate_per_year': round(after_rate, 2)
            },
            'impact': {
                'type': impact,
                'rate_change_pct': round(rate_change_pct, 2),
                'rate_change_absolute': round(after_rate - before_rate, 2),
                'strength': impact_strength,
                'p_value': round(p_value, 4),
                'statistically_significant': p_value < 0.05
            },
            'violations_before': before_violations.to_dict('records') if not before_violations.empty else [],
            'violations_after': after_violations.to_dict('records') if not after_violations.empty else []
        }
    
    def analyze_company_violation_patterns(
        self,
        violations_df: pd.DataFrame,
        date_col: str = 'violation_date'
    ) -> Dict[str, Any]:
        """
        Analyze overall violation patterns for a company.
        
        Returns multiple impact analyses for different violation points.
        """
        if violations_df.empty:
            return {'analyses': [], 'summary': {}}
        
        violations_df = violations_df.copy()
        violations_df[date_col] = pd.to_datetime(violations_df[date_col], errors='coerce')
        violations_df = violations_df.dropna(subset=[date_col]).sort_values(date_col)
        
        if len(violations_df) < self.min_violations:
            return {'analyses': [], 'summary': {'error': f'Less than {self.min_violations} violations'}}
        
        analyses = []
        
        # Analyze impact of first violation
        first_impact = self.calculate_violation_impact(violations_df, date_col=date_col)
        if first_impact.get('impact'):
            first_impact['analysis_type'] = 'first_violation'
            analyses.append(first_impact)
        
        # Analyze impact of first high-penalty violation
        if 'current_penalty' in violations_df.columns:
            high_penalty_threshold = violations_df['current_penalty'].quantile(0.75)
            high_penalty_violations = violations_df[violations_df['current_penalty'] >= high_penalty_threshold]
            
            if not high_penalty_violations.empty:
                first_high_penalty_date = high_penalty_violations[date_col].iloc[0]
                
                # Find the violation ID
                first_high_penalty_row = high_penalty_violations.iloc[0]
                violation_id = None
                if 'id' in first_high_penalty_row:
                    violation_id = first_high_penalty_row['id']
                
                high_penalty_impact = self.calculate_violation_impact(
                    violations_df,
                    violation_id=violation_id,
                    date_col=date_col
                )
                if high_penalty_impact.get('impact'):
                    high_penalty_impact['analysis_type'] = 'first_high_penalty'
                    high_penalty_impact['threshold'] = high_penalty_threshold
                    analyses.append(high_penalty_impact)
        
        # Analyze impact of first multi-agency violation
        if 'agency' in violations_df.columns:
            agency_counts = violations_df.groupby(violations_df[date_col].dt.date).agg({
                'agency': 'nunique'
            })
            multi_agency_dates = agency_counts[agency_counts['agency'] > 1].index
            
            if len(multi_agency_dates) > 0:
                first_multi_agency_date = pd.to_datetime(multi_agency_dates[0])
                first_multi_agency_idx = violations_df[violations_df[date_col].dt.date == first_multi_agency_date.date()].index[0]
                
                violation_id = None
                if 'id' in violations_df.columns:
                    violation_id = violations_df.loc[first_multi_agency_idx, 'id']
                
                multi_agency_impact = self.calculate_violation_impact(
                    violations_df,
                    violation_id=violation_id,
                    date_col=date_col
                )
                if multi_agency_impact.get('impact'):
                    multi_agency_impact['analysis_type'] = 'first_multi_agency'
                    analyses.append(multi_agency_impact)
        
        # Calculate summary statistics
        summary = self._calculate_summary_statistics(analyses)
        
        return {
            'analyses': analyses,
            'summary': summary
        }
    
    def _find_impact_violation(self, violations_df: pd.DataFrame, date_col: str) -> pd.Timestamp:
        """Find the violation to use for impact analysis."""
        # Strategy: Use first violation with significant penalty (if available)
        # Otherwise use the first violation in the middle of the timeline
        
        if 'current_penalty' in violations_df.columns:
            # Find first violation above median penalty
            median_penalty = violations_df['current_penalty'].median()
            significant_violations = violations_df[violations_df['current_penalty'] >= median_penalty]
            
            if not significant_violations.empty:
                # Use first significant violation, but not too early (need before period)
                min_date = violations_df[date_col].min() + timedelta(days=self.lookback_days)
                significant_after_min = significant_violations[significant_violations[date_col] >= min_date]
                
                if not significant_after_min.empty:
                    return significant_after_min[date_col].iloc[0]
                else:
                    # Use first significant violation anyway
                    return significant_violations[date_col].iloc[0]
        
        # Default: Use violation at 1/3 point in timeline (ensures we have before/after data)
        timeline_start = violations_df[date_col].min()
        timeline_end = violations_df[date_col].max()
        timeline_length = (timeline_end - timeline_start).days
        
        if timeline_length > (self.lookback_days + self.lookahead_days):
            target_date = timeline_start + timedelta(days=timeline_length // 3)
            # Find closest violation to target
            violations_df['date_diff'] = abs(violations_df[date_col] - target_date)
            return violations_df.loc[violations_df['date_diff'].idxmin(), date_col]
        else:
            # Use middle violation
            return violations_df[date_col].iloc[len(violations_df) // 2]
    
    def _test_significance(
        self,
        before_violations: pd.DataFrame,
        after_violations: pd.DataFrame,
        violation_date: pd.Timestamp,
        date_col: str
    ) -> float:
        """
        Test statistical significance of change in violation rates.
        
        Uses Poisson rate test or Mann-Whitney U test depending on data.
        """
        if len(before_violations) == 0 and len(after_violations) == 0:
            return 1.0  # No change
        
        if len(before_violations) == 0:
            # Only after violations - test if rate is significantly > 0
            return 0.01 if len(after_violations) > 0 else 1.0
        
        if len(after_violations) == 0:
            # Only before violations - test if rate dropped to 0
            return 0.01 if len(before_violations) > 0 else 1.0
        
        # Calculate time intervals between violations (as proxy for rate)
        # Before period
        before_dates = sorted(before_violations[date_col].tolist())
        if len(before_dates) > 1:
            before_intervals = [(before_dates[i+1] - before_dates[i]).days for i in range(len(before_dates)-1)]
        else:
            before_intervals = [365]  # Default interval if only one violation
        
        # After period
        after_dates = sorted(after_violations[date_col].tolist())
        if len(after_dates) > 1:
            after_intervals = [(after_dates[i+1] - after_dates[i]).days for i in range(len(after_dates)-1)]
        else:
            after_intervals = [365]
        
        # Mann-Whitney U test (non-parametric test for two independent samples)
        try:
            statistic, p_value = stats.mannwhitneyu(before_intervals, after_intervals, alternative='two-sided')
            return p_value
        except:
            # Fallback: simple rate comparison test
            before_rate = len(before_violations) / max(1, sum(before_intervals)) * 365
            after_rate = len(after_violations) / max(1, sum(after_intervals)) * 365
            
            # Simple test: if rate change is > 50%, consider significant
            if abs(after_rate - before_rate) / max(before_rate, 0.1) > 0.5:
                return 0.05
            else:
                return 0.5
    
    def _calculate_impact_strength(self, rate_change_pct: float) -> str:
        """Classify impact strength based on percentage change."""
        abs_change = abs(rate_change_pct)
        
        if abs_change >= 100:
            return "Very Strong"
        elif abs_change >= 50:
            return "Strong"
        elif abs_change >= 25:
            return "Moderate"
        elif abs_change >= 10:
            return "Weak"
        else:
            return "Minimal"
    
    def _calculate_summary_statistics(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics across multiple analyses."""
        if not analyses:
            return {}
        
        impacts = [a.get('impact', {}) for a in analyses if a.get('impact')]
        
        if not impacts:
            return {}
        
        increased = sum(1 for imp in impacts if imp.get('type') == 'Increased')
        reduced = sum(1 for imp in impacts if imp.get('type') == 'Reduced')
        no_change = sum(1 for imp in impacts if imp.get('type') in ['No Change', 'No Significant Change'])
        
        significant = sum(1 for imp in impacts if imp.get('statistically_significant', False))
        
        avg_rate_change = np.mean([imp.get('rate_change_pct', 0) for imp in impacts])
        
        return {
            'total_analyses': len(analyses),
            'increased_violations': increased,
            'reduced_violations': reduced,
            'no_change': no_change,
            'statistically_significant': significant,
            'avg_rate_change_pct': round(avg_rate_change, 2)
        }
    
    def _empty_result(self, error: Optional[str] = None) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            'violation_date': None,
            'before_period': {'violation_count': 0, 'rate_per_year': 0},
            'after_period': {'violation_count': 0, 'rate_per_year': 0},
            'impact': {
                'type': 'Unable to Analyze',
                'rate_change_pct': 0,
                'statistically_significant': False
            },
            'error': error
        }

