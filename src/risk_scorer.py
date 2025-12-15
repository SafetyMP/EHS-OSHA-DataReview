"""
Risk Scoring System
Calculates composite risk scores for companies based on violation history.
"""

from typing import Dict, Any, Optional, List
import pandas as pd
from datetime import datetime, timedelta
import numpy as np


class RiskScorer:
    """Calculate risk scores for companies based on compliance history."""
    
    def __init__(
        self,
        violation_weight: float = 0.30,
        penalty_weight: float = 0.25,
        recency_weight: float = 0.20,
        severity_weight: float = 0.15,
        multi_agency_weight: float = 0.10
    ):
        """
        Initialize risk scorer with customizable weights.
        
        Args:
            violation_weight: Weight for violation count (0-1)
            penalty_weight: Weight for total penalties (0-1)
            recency_weight: Weight for recent violations (0-1)
            severity_weight: Weight for severity (repeat violations, high penalties) (0-1)
            multi_agency_weight: Weight for violations across multiple agencies (0-1)
        
        Note: Weights should sum to approximately 1.0 for meaningful scores
        """
        self.weights = {
            'violation_count': violation_weight,
            'penalties': penalty_weight,
            'recency': recency_weight,
            'severity': severity_weight,
            'multi_agency': multi_agency_weight
        }
    
    def calculate_violation_score(self, violation_count: int, max_count: int = 1000) -> float:
        """
        Calculate score based on number of violations (0-100).
        
        Uses logarithmic scaling to prevent extremely high violation counts from
        dominating the score.
        """
        if violation_count == 0:
            return 0.0
        
        # Logarithmic scaling: log(1 + violations) / log(1 + max) * 100
        score = min(np.log1p(violation_count) / np.log1p(max_count) * 100, 100)
        return round(score, 2)
    
    def calculate_penalty_score(self, total_penalties: float, max_penalty: float = 1000000) -> float:
        """
        Calculate score based on total penalties (0-100).
        
        Uses logarithmic scaling for penalty amounts.
        """
        if total_penalties == 0:
            return 0.0
        
        # Logarithmic scaling
        score = min(np.log1p(total_penalties) / np.log1p(max_penalty) * 100, 100)
        return round(score, 2)
    
    def calculate_recency_score(
        self, 
        violations_df: pd.DataFrame,
        current_date: Optional[datetime] = None
    ) -> float:
        """
        Calculate score based on recency of violations (0-100).
        
        More recent violations contribute more to the score.
        """
        if violations_df.empty or 'violation_date' not in violations_df.columns:
            return 0.0
        
        current_date = current_date or datetime.now()
        
        # Calculate days since most recent violation
        violations_df = violations_df.copy()
        violations_df['violation_date'] = pd.to_datetime(violations_df['violation_date'], errors='coerce')
        violations_df = violations_df.dropna(subset=['violation_date'])
        
        if violations_df.empty:
            return 0.0
        
        most_recent = violations_df['violation_date'].max()
        days_since = (current_date - most_recent).days
        
        # Score decreases with time: 100 if within 30 days, 0 if > 730 days (2 years)
        if days_since <= 30:
            score = 100.0
        elif days_since >= 730:
            score = 0.0
        else:
            # Linear decay between 30 and 730 days
            score = 100 * (1 - (days_since - 30) / 700)
        
        return round(max(0, score), 2)
    
    def calculate_severity_score(self, violations_df: pd.DataFrame) -> float:
        """
        Calculate score based on violation severity (0-100).
        
        Factors:
        - High penalty violations
        - Repeat violations of same type
        - Average penalty per violation
        """
        if violations_df.empty:
            return 0.0
        
        score = 0.0
        factors = 0
        
        # Factor 1: Average penalty per violation
        if 'current_penalty' in violations_df.columns:
            avg_penalty = violations_df['current_penalty'].fillna(0).mean()
            # Normalize: $0-10k = 0-33, $10k-50k = 33-66, $50k+ = 66-100
            penalty_score = min(avg_penalty / 50000 * 100, 100) if avg_penalty > 0 else 0
            score += penalty_score * 0.5
            factors += 0.5
        
        # Factor 2: High penalty violations (>$25k each)
        if 'current_penalty' in violations_df.columns:
            high_penalty_count = (violations_df['current_penalty'].fillna(0) > 25000).sum()
            high_penalty_ratio = high_penalty_count / len(violations_df)
            high_penalty_score = high_penalty_ratio * 100
            score += high_penalty_score * 0.3
            factors += 0.3
        
        # Factor 3: Repeat violations (same standard)
        if 'standard' in violations_df.columns:
            standard_counts = violations_df['standard'].value_counts()
            repeat_violations = (standard_counts > 1).sum()
            if len(violations_df) > 0:
                repeat_ratio = repeat_violations / len(violations_df)
                repeat_score = min(repeat_ratio * 200, 100)  # Up to 50% repeats = 100 points
                score += repeat_score * 0.2
                factors += 0.2
        
        # Normalize by factors applied
        if factors > 0:
            score = score / factors
        
        return round(min(score, 100), 2)
    
    def calculate_multi_agency_score(self, agencies: List[str]) -> float:
        """
        Calculate score based on violations across multiple agencies (0-100).
        
        Companies with violations in multiple agencies are higher risk.
        """
        if not agencies:
            return 0.0
        
        unique_agencies = len(set(agencies))
        
        # Score: 0 for 1 agency, 50 for 2, 75 for 3, 100 for 4+
        if unique_agencies == 1:
            return 0.0
        elif unique_agencies == 2:
            return 50.0
        elif unique_agencies == 3:
            return 75.0
        else:
            return 100.0
    
    def calculate_composite_score(
        self,
        violations_df: pd.DataFrame,
        max_violation_count: Optional[int] = None,
        max_penalty: Optional[float] = None,
        current_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate composite risk score for a company.
        
        Args:
            violations_df: DataFrame with violation records
            max_violation_count: Maximum violation count for normalization (auto-calculated if None)
            max_penalty: Maximum penalty for normalization (auto-calculated if None)
            current_date: Current date for recency calculation (uses now() if None)
        
        Returns:
            Dictionary with:
            - composite_score: Overall risk score (0-100)
            - component_scores: Individual component scores
            - risk_level: "Low", "Medium", "High", "Critical"
            - factors: Detailed breakdown
        """
        if violations_df.empty:
            return {
                'composite_score': 0.0,
                'risk_level': 'Low',
                'component_scores': {
                    'violation_count': 0.0,
                    'penalties': 0.0,
                    'recency': 0.0,
                    'severity': 0.0,
                    'multi_agency': 0.0
                },
                'factors': {
                    'violation_count': 0,
                    'total_penalties': 0.0,
                    'avg_penalty': 0.0,
                    'agencies': [],
                    'most_recent_violation': None
                }
            }
        
        # Calculate component scores
        violation_count = len(violations_df)
        violation_score = self.calculate_violation_score(
            violation_count,
            max_count=max_violation_count or 1000
        )
        
        # Penalty calculations
        total_penalties = 0.0
        avg_penalty = 0.0
        if 'current_penalty' in violations_df.columns:
            total_penalties = violations_df['current_penalty'].fillna(0).sum()
            avg_penalty = violations_df['current_penalty'].fillna(0).mean()
        
        penalty_score = self.calculate_penalty_score(
            total_penalties,
            max_penalty=max_penalty or 1000000
        )
        
        # Recency score
        recency_score = self.calculate_recency_score(violations_df, current_date)
        
        # Severity score
        severity_score = self.calculate_severity_score(violations_df)
        
        # Multi-agency score
        agencies = []
        if 'agency' in violations_df.columns:
            agencies = violations_df['agency'].dropna().unique().tolist()
        
        multi_agency_score = self.calculate_multi_agency_score(agencies)
        
        # Calculate weighted composite score
        composite_score = (
            violation_score * self.weights['violation_count'] +
            penalty_score * self.weights['penalties'] +
            recency_score * self.weights['recency'] +
            severity_score * self.weights['severity'] +
            multi_agency_score * self.weights['multi_agency']
        )
        
        composite_score = round(min(composite_score, 100), 2)
        
        # Determine risk level
        if composite_score >= 75:
            risk_level = 'Critical'
        elif composite_score >= 50:
            risk_level = 'High'
        elif composite_score >= 25:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'
        
        # Most recent violation date
        most_recent = None
        if 'violation_date' in violations_df.columns:
            dates = pd.to_datetime(violations_df['violation_date'], errors='coerce')
            dates = dates.dropna()
            if not dates.empty:
                most_recent = dates.max()
                if pd.notna(most_recent):
                    most_recent = most_recent.strftime('%Y-%m-%d')
        
        return {
            'composite_score': composite_score,
            'risk_level': risk_level,
            'component_scores': {
                'violation_count': violation_score,
                'penalties': penalty_score,
                'recency': recency_score,
                'severity': severity_score,
                'multi_agency': multi_agency_score
            },
            'factors': {
                'violation_count': violation_count,
                'total_penalties': round(total_penalties, 2),
                'avg_penalty': round(avg_penalty, 2),
                'agencies': agencies,
                'most_recent_violation': most_recent,
                'unique_agencies': len(set(agencies)) if agencies else 0
            }
        }
    
    def calculate_industry_benchmark(
        self,
        company_violations: pd.DataFrame,
        industry_violations: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Compare company risk score against industry average.
        
        Returns percentile ranking and comparison metrics.
        """
        company_score = self.calculate_composite_score(company_violations)
        
        # Calculate scores for industry peers (sample if too large)
        if len(industry_violations) > 1000:
            industry_violations = industry_violations.sample(1000)
        
        # Group by company and calculate scores
        company_names = industry_violations.get('company_name_normalized', 
                                                industry_violations.get('company_name', 
                                                                      pd.Series(['industry'])))
        
        industry_scores = []
        for company in company_names.unique():
            company_df = industry_violations[company_names == company]
            if not company_df.empty:
                score_data = self.calculate_composite_score(company_df)
                industry_scores.append(score_data['composite_score'])
        
        if not industry_scores:
            return {
                'company_score': company_score['composite_score'],
                'industry_avg': 0.0,
                'industry_median': 0.0,
                'percentile': 50.0,
                'comparison': 'No industry data available'
            }
        
        industry_avg = np.mean(industry_scores)
        industry_median = np.median(industry_scores)
        
        # Calculate percentile
        percentile = (sum(1 for s in industry_scores if s < company_score['composite_score']) / 
                     len(industry_scores) * 100)
        
        comparison = 'Average'
        if company_score['composite_score'] > industry_avg * 1.5:
            comparison = 'Much Higher Risk'
        elif company_score['composite_score'] > industry_avg:
            comparison = 'Higher Risk'
        elif company_score['composite_score'] < industry_avg * 0.5:
            comparison = 'Much Lower Risk'
        elif company_score['composite_score'] < industry_avg:
            comparison = 'Lower Risk'
        
        return {
            'company_score': company_score['composite_score'],
            'industry_avg': round(industry_avg, 2),
            'industry_median': round(industry_median, 2),
            'percentile': round(percentile, 1),
            'comparison': comparison
        }

