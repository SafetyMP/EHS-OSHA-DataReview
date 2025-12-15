# Running Amazon Compliance Analysis Test

## Quick Start (Using Streamlit App)

The easiest way to test Amazon analysis is through the Streamlit dashboard:

```bash
# 1. Install dependencies (if not already installed)
pip install -r requirements.txt

# 2. Make sure you have OSHA data downloaded
python src/data_loader.py

# 3. (Optional) Migrate to database for better performance
python -m src.db_migration

# 4. Launch the dashboard
streamlit run app.py
```

Then:
1. Navigate to the **"Company Comparison"** tab
2. Enter **"Amazon"** in the company search box
3. Adjust the fuzzy matching threshold if needed (start with 70-75)
4. Click **"Search Company"**
5. Review the results including:
   - Violations found
   - Risk score
   - Cross-agency comparison
   - Violation impact analysis

## Running the Test Script

If you want to run the test script directly:

```bash
# Install dependencies first
pip install -r requirements.txt

# Run the test
python scripts/test_amazon.py
```

Or if using Python 3 explicitly:

```bash
python3 scripts/test_amazon.py
```

## What the Test Does

The test script will:

1. **Search for Amazon** using fuzzy matching
   - Tries variations like "Amazon.com", "Amazon Services LLC", etc.
   - Shows matched company names with similarity scores

2. **Calculate Risk Score**
   - Composite risk score (0-100)
   - Component scores breakdown
   - Risk factors (violations, penalties, agencies)

3. **Cross-Agency Comparison**
   - Total violations across all agencies
   - Breakdown by agency (OSHA, EPA, MSHA, FDA)
   - Penalty summaries

4. **Violation Impact Analysis**
   - Whether violations increased or reduced subsequent violations
   - Statistical significance testing
   - Before/after period comparisons

## Expected Results

### If Amazon Has Violations:
- You'll see violation counts, risk scores, and impact analyses
- Results will be broken down by agency
- Visualizations will show trends and comparisons

### If Amazon Has No Violations:
- You may see "No violations found"
- Try variations: "Amazon.com", "Amazon Services", "Amazon.com Services LLC"
- Lower the fuzzy matching threshold to 60-65
- Check that data is properly loaded

## Troubleshooting

### No violations found?
1. **Check data is loaded:**
   ```bash
   python src/data_loader.py
   ```

2. **Try different name variations:**
   - Amazon
   - Amazon.com
   - Amazon Services LLC
   - Amazon.com Services LLC
   - Amazon Web Services

3. **Adjust fuzzy matching threshold:**
   - Lower threshold (60-70) = more matches, may include false positives
   - Higher threshold (80-90) = stricter matching

4. **Check database (if using):**
   ```bash
   python -m src.db_migration --stats
   ```

### Import errors?
```bash
# Install all dependencies
pip install -r requirements.txt

# Or install individually:
pip install pandas numpy streamlit plotly requests python-dateutil sqlalchemy rapidfuzz scipy
```

### Database errors?
If you're getting database-related errors:
1. Make sure SQLite is available (usually built into Python)
2. Or use CSV-based analyzer instead:
   ```python
   from src.analyzer import OSHAAnalyzer
   analyzer = OSHAAnalyzer()  # Uses CSV instead of database
   ```

## Alternative: Direct Python Usage

You can also test directly in Python:

```python
from src.compliance_analyzer import ComplianceAnalyzer

# Initialize
analyzer = ComplianceAnalyzer()

# Search for Amazon
results = analyzer.search_company("Amazon", use_fuzzy=True, fuzzy_threshold=70)
print(f"Found {len(results)} violations")

# Get risk score
risk = analyzer.get_company_risk_score("Amazon")
print(f"Risk Score: {risk['composite_score']}/100")
print(f"Risk Level: {risk['risk_level']}")

# Compare across agencies
comparison = analyzer.compare_company_across_agencies("Amazon", include_risk_score=True)
print(f"Total violations: {comparison['total_violations']}")

# Analyze impact
impact = analyzer.analyze_violation_impact("Amazon")
print(impact['impact_analysis']['summary'])
```

## Notes

- Amazon may appear under various legal entity names in the data
- Fuzzy matching helps find all variations
- Results depend on what's actually in the OSHA/enforcement databases
- If Amazon has no violations in the dataset, you won't find any results (this is expected)

