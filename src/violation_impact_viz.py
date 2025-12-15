"""
Visualization functions for violation impact analysis.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from typing import Dict, Any, List
from datetime import datetime


def plot_violation_timeline(
    violations_df: pd.DataFrame,
    impact_date: str,
    before_period: Dict[str, Any],
    after_period: Dict[str, Any],
    date_col: str = 'violation_date'
) -> go.Figure:
    """
    Create timeline visualization showing violations before and after impact date.
    
    Args:
        violations_df: DataFrame with violations
        impact_date: Date of the violation being analyzed
        before_period: Before period data
        after_period: After period data
        date_col: Column name for dates
    
    Returns:
        Plotly figure
    """
    violations_df = violations_df.copy()
    violations_df[date_col] = pd.to_datetime(violations_df[date_col], errors='coerce')
    violations_df = violations_df.dropna(subset=[date_col]).sort_values(date_col)
    
    impact_dt = pd.to_datetime(impact_date)
    
    # Split violations
    before_violations = violations_df[violations_df[date_col] < impact_dt]
    after_violations = violations_df[violations_df[date_col] > impact_dt]
    
    fig = go.Figure()
    
    # Before period violations
    if not before_violations.empty:
        fig.add_trace(go.Scatter(
            x=before_violations[date_col],
            y=[1] * len(before_violations),
            mode='markers',
            name='Before Period',
            marker=dict(color='blue', size=10, symbol='circle'),
            hovertemplate='Date: %{x}<br>Violation<extra></extra>'
        ))
    
    # Impact violation
    impact_violation = violations_df[violations_df[date_col] == impact_dt]
    if not impact_violation.empty:
        fig.add_trace(go.Scatter(
            x=[impact_dt],
            y=[1],
            mode='markers',
            name='Impact Violation',
            marker=dict(color='red', size=15, symbol='star'),
            hovertemplate=f'Impact Date: {impact_date}<extra></extra>'
        ))
    
    # After period violations
    if not after_violations.empty:
        fig.add_trace(go.Scatter(
            x=after_violations[date_col],
            y=[1] * len(after_violations),
            mode='markers',
            name='After Period',
            marker=dict(color='green', size=10, symbol='circle'),
            hovertemplate='Date: %{x}<br>Violation<extra></extra>'
        ))
    
    # Add vertical line at impact date
    fig.add_vline(
        x=impact_dt,
        line_dash="dash",
        line_color="red",
        annotation_text="Impact Date",
        annotation_position="top"
    )
    
    # Shade before/after periods
    before_start = pd.to_datetime(before_period.get('start_date', violations_df[date_col].min()))
    fig.add_vrect(
        x0=before_start,
        x1=impact_dt,
        fillcolor="blue",
        opacity=0.1,
        layer="below",
        line_width=0,
        annotation_text="Before Period",
        annotation_position="top left"
    )
    
    after_end = pd.to_datetime(after_period.get('end_date', violations_df[date_col].max()))
    fig.add_vrect(
        x0=impact_dt,
        x1=after_end,
        fillcolor="green",
        opacity=0.1,
        layer="below",
        line_width=0,
        annotation_text="After Period",
        annotation_position="top right"
    )
    
    fig.update_layout(
        title="Violation Timeline: Before and After Impact",
        xaxis_title="Date",
        yaxis_title="",
        yaxis=dict(showticklabels=False, range=[0.5, 1.5]),
        hovermode='closest',
        height=400
    )
    
    return fig


def plot_rate_comparison(
    before_period: Dict[str, Any],
    after_period: Dict[str, Any],
    impact: Dict[str, Any]
) -> go.Figure:
    """
    Create bar chart comparing violation rates before and after.
    
    Args:
        before_period: Before period data
        after_period: After period data
        impact: Impact analysis results
    
    Returns:
        Plotly figure
    """
    periods = ['Before', 'After']
    rates = [
        before_period.get('rate_per_year', 0),
        after_period.get('rate_per_year', 0)
    ]
    counts = [
        before_period.get('violation_count', 0),
        after_period.get('violation_count', 0)
    ]
    
    impact_type = impact.get('type', 'Unknown')
    
    # Color based on impact
    colors = ['blue', 'green'] if impact_type == 'Reduced' else ['blue', 'red']
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=periods,
        y=rates,
        name='Rate per Year',
        marker_color=colors,
        text=[f"{r:.2f}/year<br>({c} violations)" for r, c in zip(rates, counts)],
        textposition='outside',
        hovertemplate='Period: %{x}<br>Rate: %{y:.2f} violations/year<extra></extra>'
    ))
    
    impact_text = f"{impact_type}: {impact.get('rate_change_pct', 0):.1f}%"
    if impact.get('statistically_significant'):
        impact_text += " (Significant)"
    
    fig.update_layout(
        title=f"Violation Rate Comparison<br><sub>{impact_text}</sub>",
        xaxis_title="Period",
        yaxis_title="Violations per Year",
        showlegend=False,
        height=400
    )
    
    return fig


def plot_impact_summary(analyses: List[Dict[str, Any]]) -> go.Figure:
    """
    Create summary chart of multiple impact analyses.
    
    Args:
        analyses: List of impact analysis results
    
    Returns:
        Plotly figure
    """
    if not analyses:
        fig = go.Figure()
        fig.add_annotation(text="No analyses available", showarrow=False)
        return fig
    
    impact_types = []
    rate_changes = []
    significant = []
    
    for analysis in analyses:
        impact = analysis.get('impact', {})
        impact_types.append(impact.get('type', 'Unknown'))
        rate_changes.append(impact.get('rate_change_pct', 0))
        significant.append(impact.get('statistically_significant', False))
    
    # Create color mapping
    colors = []
    for imp_type, sig in zip(impact_types, significant):
        if imp_type == 'Increased':
            colors.append('red' if sig else 'lightcoral')
        elif imp_type == 'Reduced':
            colors.append('green' if sig else 'lightgreen')
        else:
            colors.append('gray')
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=[f"Analysis {i+1}" for i in range(len(analyses))],
        y=rate_changes,
        marker_color=colors,
        text=[f"{rc:+.1f}%" for rc in rate_changes],
        textposition='outside',
        hovertemplate='Analysis: %{x}<br>Change: %{y:.1f}%<extra></extra>'
    ))
    
    # Add horizontal line at 0
    fig.add_hline(y=0, line_dash="dash", line_color="black")
    
    fig.update_layout(
        title="Impact Analysis Summary",
        xaxis_title="Analysis",
        yaxis_title="Rate Change (%)",
        height=400
    )
    
    return fig

