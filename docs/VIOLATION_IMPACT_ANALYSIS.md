# Violation Impact Analysis Guide

This guide explains how to analyze whether violations increased or reduced subsequent violations by the same company.

## Overview

The violation impact analysis determines if a specific violation (or series of violations) had a measurable effect on a company's subsequent violation pattern. This helps answer questions like:
- Did enforcement actions deter future violations?
- Did high-penalty violations lead to improved compliance?
- Did violations in one area lead to more violations overall?

## How It Works

### Methodology

1. **Before/After Comparison**: Analyzes violation rates in two periods:
   - **Before Period**: Typically 365 days before the impact violation
   - **After Period**: Typically 365 days after the impact violation

2. **Rate Calculation**: Calculates violations per year for each period:
   - Before rate = (violations before / days before) × 365
   - After rate = (violations after / days after) × 365

3. **Statistical Testing**: Uses Mann-Whitney U test to determine if the change is statistically significant (p < 0.05)

4. **Impact Classification**:
   - **Increased**: After rate > Before rate (statistically significant)
   - **Reduced**: After rate < Before rate (statistically significant)
   - **No Significant Change**: Change not statistically significant

### Impact Strength

- **Very Strong**: ≥100% change
- **Strong**: 50-99% change
- **Moderate**: 25-49% change
- **Weak**: 10-24% change
- **Minimal**: <10% change

## Usage

### Basic Usage

```python
from src.compliance_analyzer import ComplianceAnalyzer

analyzer = ComplianceAnalyzer()

# Analyze violation impact for a company
impact_analysis = analyzer.analyze_violation_impact("Acme Corporation")

# Results include multiple analyses
analyses = impact_analysis['impact_analysis']['analyses']
summary = impact_analysis['impact_analysis']['summary']

# View results
for analysis in analyses:
    impact = analysis['impact']
    print(f"Type: {impact['type']}")
    print(f"Rate Change: {impact['rate_change_pct']}%")
    print(f"Significant: {impact['statistically_significant']}")
```

### Analyzing Specific Violations

```python
# Analyze impact of a specific violation
impact_analysis = analyzer.analyze_violation_impact(
    "Acme Corporation",
    violation_id="violation_12345"
)
```

### Custom Analysis Periods

```python
from src.violation_impact import ViolationImpactAnalyzer

# Create analyzer with custom periods
impact_analyzer = ViolationImpactAnalyzer(
    lookback_days=730,   # 2 years before
    lookahead_days=730,  # 2 years after
    min_violations=5     # Need at least 5 violations
)

# Get violations
violations_df = analyzer.search_company("Acme Corporation")

# Analyze
impact = impact_analyzer.calculate_violation_impact(violations_df)
```

## Types of Analyses

The system performs multiple types of analyses:

### 1. First Violation Impact

Analyzes the impact of the company's first violation on subsequent violations.

```python
impact = impact_analyzer.calculate_violation_impact(violations_df)
# Result includes analysis_type: 'first_violation'
```

### 2. First High-Penalty Violation

Analyzes the impact of the first violation with a penalty above the 75th percentile.

```python
# Automatically performed if penalty data available
# Result includes analysis_type: 'first_high_penalty'
```

### 3. First Multi-Agency Violation

Analyzes the impact of the first violation that occurred when the company had violations from multiple agencies simultaneously.

```python
# Automatically performed if multiple agencies present
# Result includes analysis_type: 'first_multi_agency'
```

## Understanding Results

### Impact Dictionary Structure

```python
{
    'violation_date': '2023-06-15',
    'before_period': {
        'start_date': '2022-06-15',
        'end_date': '2023-06-15',
        'days': 365,
        'violation_count': 5,
        'rate_per_year': 5.0
    },
    'after_period': {
        'start_date': '2023-06-15',
        'end_date': '2024-06-15',
        'days': 365,
        'violation_count': 2,
        'rate_per_year': 2.0
    },
    'impact': {
        'type': 'Reduced',
        'rate_change_pct': -60.0,  # 60% reduction
        'rate_change_absolute': -3.0,
        'strength': 'Strong',
        'p_value': 0.0234,  # Statistically significant
        'statistically_significant': True
    }
}
```

### Interpreting Results

1. **Positive rate_change_pct**: Violations increased
   - May indicate enforcement didn't deter violations
   - Could suggest systematic compliance issues

2. **Negative rate_change_pct**: Violations reduced
   - May indicate enforcement was effective
   - Could suggest company improved compliance

3. **p_value < 0.05**: Statistically significant
   - Change is unlikely due to random variation
   - More confident in the impact assessment

4. **p_value >= 0.05**: Not statistically significant
   - Change could be due to random variation
   - Less confident in impact assessment

## Examples

### Example 1: Successful Deterrence

```python
# Company had 10 violations in year before, 2 in year after
impact = {
    'type': 'Reduced',
    'rate_change_pct': -80.0,
    'strength': 'Very Strong',
    'statistically_significant': True,
    'p_value': 0.001
}
# Interpretation: Violations significantly reduced after enforcement action
```

### Example 2: No Effect

```python
# Company had 5 violations in year before, 5 in year after
impact = {
    'type': 'No Significant Change',
    'rate_change_pct': 0.0,
    'statistically_significant': False,
    'p_value': 0.85
}
# Interpretation: Enforcement had no measurable effect
```

### Example 3: Increased Violations

```python
# Company had 3 violations in year before, 8 in year after
impact = {
    'type': 'Increased',
    'rate_change_pct': 166.7,
    'strength': 'Very Strong',
    'statistically_significant': True,
    'p_value': 0.012
}
# Interpretation: Violations significantly increased (may indicate systemic issues)
```

## Limitations

1. **Correlation vs. Causation**: This analysis shows correlation, not causation. Other factors may contribute to changes.

2. **Minimum Data Requirements**: Needs sufficient violations (default: 3+) and time periods for meaningful analysis.

3. **External Factors**: Doesn't account for:
   - Economic conditions
   - Industry changes
   - Management changes
   - Regulatory changes

4. **Time Windows**: Fixed time windows (365 days) may not capture long-term effects.

5. **Multiple Violations**: If multiple significant violations occur close together, isolating individual impacts is difficult.

## Best Practices

1. **Use Multiple Analyses**: Review all analysis types (first violation, high penalty, multi-agency) for comprehensive view.

2. **Consider Context**: Combine with company financial data, industry trends, and other factors.

3. **Statistical Significance**: Focus on statistically significant results, but also consider practical significance.

4. **Time Periods**: Adjust lookback/lookahead periods based on your analysis needs.

5. **Visualization**: Use timeline and rate comparison charts to better understand patterns.

## In the Streamlit App

1. Go to "Company Comparison" tab
2. Search for a company
3. Click "Analyze Violation Impact" button
4. Review:
   - Summary metrics (increased/reduced counts)
   - Individual analyses with before/after comparisons
   - Statistical significance indicators
   - Visualizations (timeline, rate comparison)

## Advanced Usage

### Custom Impact Analyzer

```python
from src.violation_impact import ViolationImpactAnalyzer

# Create with custom parameters
analyzer = ViolationImpactAnalyzer(
    lookback_days=180,    # 6 months
    lookahead_days=540,   # 18 months (longer to see effects)
    min_violations=10     # Need more data for confidence
)

# Analyze specific violation
impact = analyzer.calculate_violation_impact(
    violations_df,
    violation_id="specific_violation_id"
)
```

### Batch Analysis

```python
# Analyze multiple companies
companies = ["Company A", "Company B", "Company C"]
results = []

for company in companies:
    impact = analyzer.analyze_violation_impact(company)
    results.append({
        'company': company,
        'impact': impact['impact_analysis']['summary']
    })

# Find companies where enforcement was most effective
effective = [r for r in results if r['impact'].get('reduced_violations', 0) > 0]
```

