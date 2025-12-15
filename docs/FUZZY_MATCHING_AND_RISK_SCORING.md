# Fuzzy Matching & Risk Scoring Guide

This guide explains the fuzzy company name matching and risk scoring features.

## Fuzzy Company Name Matching

### Overview

Fuzzy matching helps find companies even when names have variations, typos, or different formatting. For example:
- "Acme Corporation" matches "Acme Corp"
- "ABC Inc." matches "ABC Incorporated"
- "Smith & Company" matches "Smith Company"

### How It Works

The fuzzy matcher uses multiple algorithms:
1. **Token-based matching** - Matches words regardless of order
2. **Partial matching** - Finds partial name matches
3. **Normalized comparison** - Removes legal suffixes (Inc, LLC, Corp, etc.)
4. **Weighted scoring** - Combines multiple methods for best results

### Usage

#### In Code

```python
from src.compliance_analyzer import ComplianceAnalyzer

analyzer = ComplianceAnalyzer(fuzzy_threshold=75)  # 75% minimum similarity

# Search with fuzzy matching (default)
results = analyzer.search_company(
    "Acme Corporation",
    use_fuzzy=True,
    fuzzy_threshold=75  # 0-100, higher = stricter
)

# Results include similarity scores
if 'similarity_score' in results.columns:
    print(results[['company_name', 'similarity_score']])
```

#### Adjusting Threshold

- **50-60**: Very lenient - finds many variations (may include false positives)
- **70-80**: Balanced - good default (recommended)
- **85-95**: Strict - only very similar names
- **95-100**: Nearly exact matches only

#### Finding Similar Companies

```python
from src.fuzzy_matcher import CompanyNameMatcher

matcher = CompanyNameMatcher(threshold=80)

# Find matches from a list
candidates = ["Acme Corp", "Acme Corporation", "ABC Inc"]
matches = matcher.find_matches("Acme Corporation", candidates)
# Returns: [("Acme Corporation", 100.0), ("Acme Corp", 95.0)]

# Group similar company names
similar_groups = matcher.group_similar_companies(
    ["Acme Corp", "Acme Corporation", "ABC Inc"],
    threshold=85
)
```

## Risk Scoring System

### Overview

The risk scoring system calculates a composite risk score (0-100) for companies based on their compliance history. Higher scores indicate higher risk.

### Score Components

The risk score combines five weighted factors:

1. **Violation Count (30% weight)**
   - Number of total violations
   - Logarithmic scaling prevents extreme counts from dominating

2. **Penalty Amount (25% weight)**
   - Total penalties assessed
   - Logarithmic scaling for penalty amounts

3. **Recency (20% weight)**
   - How recent are the violations?
   - Recent violations (< 30 days) score highest
   - Older violations (> 2 years) score lower

4. **Severity (15% weight)**
   - Average penalty per violation
   - High-penalty violations (>$25k)
   - Repeat violations of same type

5. **Multi-Agency (10% weight)**
   - Violations across multiple agencies
   - 1 agency = 0, 2 agencies = 50, 3 = 75, 4+ = 100

### Risk Levels

- **0-24**: Low Risk 🟢
- **25-49**: Medium Risk 🟡
- **50-74**: High Risk 🟠
- **75-100**: Critical Risk 🔴

### Usage

#### In Code

```python
from src.compliance_analyzer import ComplianceAnalyzer
from src.risk_scorer import RiskScorer

# Using ComplianceAnalyzer (includes risk scoring)
analyzer = ComplianceAnalyzer()

# Get company comparison with risk score
summary = analyzer.compare_company_across_agencies(
    "Acme Corporation",
    include_risk_score=True
)

risk_data = summary['risk_score']
print(f"Risk Score: {risk_data['composite_score']}/100")
print(f"Risk Level: {risk_data['risk_level']}")
print(f"Components: {risk_data['component_scores']}")

# Using RiskScorer directly
scorer = RiskScorer()

# Customize weights
custom_scorer = RiskScorer(
    violation_weight=0.40,  # Emphasize violation count
    penalty_weight=0.30,
    recency_weight=0.15,
    severity_weight=0.10,
    multi_agency_weight=0.05
)

violations_df = analyzer.search_company("Acme Corporation")
risk_data = custom_scorer.calculate_composite_score(violations_df)
```

#### Understanding Component Scores

```python
risk_data = analyzer.get_company_risk_score("Acme Corporation")

print("Component Scores:")
for component, score in risk_data['component_scores'].items():
    print(f"  {component}: {score}/100")

print("\nRisk Factors:")
factors = risk_data['factors']
print(f"  Violations: {factors['violation_count']}")
print(f"  Total Penalties: ${factors['total_penalties']:,.2f}")
print(f"  Avg Penalty: ${factors['avg_penalty']:,.2f}")
print(f"  Agencies: {factors['unique_agencies']} ({', '.join(factors['agencies'])})")
print(f"  Most Recent: {factors['most_recent_violation']}")
```

#### Industry Benchmarking

```python
from src.risk_scorer import RiskScorer

scorer = RiskScorer()

# Get company violations
company_violations = analyzer.search_company("Acme Corporation")

# Get industry violations (e.g., same NAICS code)
industry_violations = analyzer.search_violations(naics_prefix="31")  # Manufacturing

# Compare
benchmark = scorer.calculate_industry_benchmark(
    company_violations,
    industry_violations
)

print(f"Company Score: {benchmark['company_score']}")
print(f"Industry Average: {benchmark['industry_avg']}")
print(f"Percentile: {benchmark['percentile']}%")
print(f"Comparison: {benchmark['comparison']}")
```

### Customizing Risk Scoring

#### Adjusting Weights

```python
# Emphasize recent violations
scorer = RiskScorer(
    violation_weight=0.20,
    penalty_weight=0.20,
    recency_weight=0.40,  # Increased
    severity_weight=0.10,
    multi_agency_weight=0.10
)

# Emphasize multi-agency violations
scorer = RiskScorer(
    violation_weight=0.25,
    penalty_weight=0.25,
    recency_weight=0.15,
    severity_weight=0.15,
    multi_agency_weight=0.20  # Increased
)
```

#### Normalization Thresholds

The scorer uses default normalization values:
- Max violations: 1,000 (logarithmic scale)
- Max penalty: $1,000,000 (logarithmic scale)

You can adjust these when calculating scores:

```python
risk_data = scorer.calculate_composite_score(
    violations_df,
    max_violation_count=500,  # Lower threshold = violations score higher
    max_penalty=500000         # Lower threshold = penalties score higher
)
```

## In the Streamlit App

### Fuzzy Matching

1. Go to the "Company Comparison" tab
2. Enter a company name
3. Adjust the "Fuzzy Matching Threshold" slider (50-100)
4. Click "Search Company"
5. Results show similarity scores and top matches

### Risk Scoring

1. Search for a company (fuzzy matching recommended)
2. Risk score appears in the metrics at the top
3. Click to see detailed breakdown:
   - Component scores (bar charts)
   - Risk factors (violations, penalties, agencies)
   - Risk level indicator

## Best Practices

### Fuzzy Matching

1. **Start with default threshold (75)** and adjust based on results
2. **Review similarity scores** to verify match quality
3. **Use stricter thresholds** for exact company lookups
4. **Use lenient thresholds** for discovery and exploration

### Risk Scoring

1. **Use composite scores** for overall risk assessment
2. **Review component scores** to understand risk drivers
3. **Compare to industry benchmarks** for context
4. **Consider custom weights** based on your risk priorities
5. **Combine with other factors** (financial data, news, etc.) for comprehensive assessment

## Example Use Cases

### Find All Variations of a Company Name

```python
matcher = CompanyNameMatcher(threshold=70)
violations_df = analyzer.search_company("Walmart", use_fuzzy=True)

# Group all variations
company_names = violations_df['company_name'].unique()
groups = matcher.group_similar_companies(company_names.tolist(), threshold=80)

for group in groups:
    print(f"Variations: {', '.join(group)}")
```

### Identify High-Risk Companies

```python
# Search for companies with violations
violations_df = analyzer.search_company("", agencies=["OSHA"])

# Calculate risk scores
scorer = RiskScorer()
high_risk_companies = []

for company in violations_df['company_name'].unique():
    company_violations = violations_df[violations_df['company_name'] == company]
    risk_data = scorer.calculate_composite_score(company_violations)
    
    if risk_data['risk_level'] in ['High', 'Critical']:
        high_risk_companies.append({
            'company': company,
            'score': risk_data['composite_score'],
            'level': risk_data['risk_level']
        })

# Sort by score
high_risk_companies.sort(key=lambda x: x['score'], reverse=True)
```

### Track Risk Trends Over Time

```python
# Calculate risk for each year
for year in range(2020, 2024):
    year_violations = violations_df[violations_df['year'] == year]
    risk_data = scorer.calculate_composite_score(year_violations)
    print(f"{year}: {risk_data['composite_score']:.1f} ({risk_data['risk_level']})")
```

## Technical Details

### Similarity Algorithms

- **Ratio**: Simple character-by-character comparison
- **Partial Ratio**: Best matching substring
- **Token Sort Ratio**: Word-based, order-independent
- **Token Set Ratio**: Word-based, ignores duplicates

Final score uses weighted average favoring token-based methods (better for company names).

### Score Calculation

1. Each component is normalized to 0-100 scale
2. Components are weighted and summed
3. Final score is capped at 100
4. Risk level determined by score ranges

### Performance

- Fuzzy matching adds minimal overhead (~10-20% for typical searches)
- Risk scoring is fast (< 100ms for typical datasets)
- Both scale well with database backend

