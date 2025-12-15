"""
Test script for Amazon compliance analysis
Tests all features: fuzzy matching, risk scoring, and violation impact analysis

Usage:
    python test_amazon.py
    
Or:
    python3 test_amazon.py

Make sure dependencies are installed:
    pip install -r requirements.txt
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.compliance_analyzer import ComplianceAnalyzer
    from src.analyzer_db import OSHAAnalyzerDB
except ImportError as e:
    print("=" * 70)
    print("IMPORT ERROR")
    print("=" * 70)
    print(f"Error: {e}")
    print("\nPlease install dependencies first:")
    print("  pip install -r requirements.txt")
    print("\nOr install individually:")
    print("  pip install pandas numpy streamlit plotly requests python-dateutil sqlalchemy rapidfuzz scipy")
    sys.exit(1)

def test_amazon_analysis():
    """Test Amazon compliance analysis with all features."""
    
    print("=" * 70)
    print("AMAZON COMPLIANCE ANALYSIS TEST")
    print("=" * 70)
    print()
    
    # Initialize analyzer
    print("Initializing compliance analyzer...")
    try:
        analyzer = ComplianceAnalyzer()
        print("✓ Analyzer initialized")
    except Exception as e:
        print(f"✗ Error initializing analyzer: {e}")
        print("\nNote: Make sure you have:")
        print("  1. Downloaded OSHA data: python src/data_loader.py")
        print("  2. Migrated to database (optional): python -m src.db_migration")
        return
    
    company_name = "Amazon"
    
    # Test 1: Basic company search with fuzzy matching
    print(f"\n{'=' * 70}")
    print("TEST 1: Company Search with Fuzzy Matching")
    print(f"{'=' * 70}")
    print(f"Searching for: '{company_name}'")
    
    try:
        results = analyzer.search_company(
            company_name,
            use_fuzzy=True,
            fuzzy_threshold=70  # Lower threshold for broader matching
        )
        
        if not results.empty:
            print(f"✓ Found {len(results)} violations")
            
            # Show unique company name matches
            if 'company_name' in results.columns:
                unique_names = results['company_name'].dropna().unique()[:10]
                print(f"\nMatched company names ({len(unique_names)} shown):")
                for name in unique_names:
                    if 'similarity_score' in results.columns:
                        scores = results[results['company_name'] == name]['similarity_score']
                        avg_score = scores.mean() if not scores.empty else 0
                        print(f"  - {name} (avg similarity: {avg_score:.1f}%)")
                    else:
                        print(f"  - {name}")
            
            # Show summary by agency
            if 'agency' in results.columns:
                print(f"\nViolations by agency:")
                agency_counts = results['agency'].value_counts()
                for agency, count in agency_counts.items():
                    print(f"  - {agency}: {count} violations")
        else:
            print("✗ No violations found")
            print("\nNote: Amazon may not have violations in the dataset, or:")
            print("  - Try variations: 'Amazon.com', 'Amazon Services LLC', etc.")
            print("  - Lower fuzzy threshold (currently 70)")
            print("  - Check if data is loaded correctly")
    except Exception as e:
        print(f"✗ Error in search: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Risk Score Calculation
    print(f"\n{'=' * 70}")
    print("TEST 2: Risk Score Calculation")
    print(f"{'=' * 70}")
    
    try:
        risk_score = analyzer.get_company_risk_score(
            company_name,
            use_fuzzy=True
        )
        
        if risk_score and 'composite_score' in risk_score:
            print(f"✓ Risk Score Calculated")
            print(f"\nComposite Risk Score: {risk_score['composite_score']}/100")
            print(f"Risk Level: {risk_score['risk_level']}")
            
            print("\nComponent Scores:")
            for component, score in risk_score.get('component_scores', {}).items():
                component_name = component.replace('_', ' ').title()
                print(f"  - {component_name}: {score:.1f}/100")
            
            print("\nRisk Factors:")
            factors = risk_score.get('factors', {})
            print(f"  - Total Violations: {factors.get('violation_count', 0)}")
            print(f"  - Total Penalties: ${factors.get('total_penalties', 0):,.2f}")
            print(f"  - Avg Penalty: ${factors.get('avg_penalty', 0):,.2f}")
            print(f"  - Agencies: {factors.get('unique_agencies', 0)} ({', '.join(factors.get('agencies', []))})")
            if factors.get('most_recent_violation'):
                print(f"  - Most Recent: {factors['most_recent_violation']}")
        else:
            print("✗ Could not calculate risk score (no violations found)")
    except Exception as e:
        print(f"✗ Error calculating risk score: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Cross-Agency Comparison
    print(f"\n{'=' * 70}")
    print("TEST 3: Cross-Agency Company Comparison")
    print(f"{'=' * 70}")
    
    try:
        comparison = analyzer.compare_company_across_agencies(
            company_name,
            include_risk_score=True,
            use_fuzzy=True
        )
        
        if comparison and 'total_violations' in comparison:
            print(f"✓ Comparison completed")
            print(f"\nTotal Violations: {comparison['total_violations']:,}")
            print(f"Total Penalties: ${comparison['total_penalties']:,.2f}")
            print(f"Agencies with Violations: {len(comparison.get('agencies', {}))}")
            
            print("\nBreakdown by Agency:")
            for agency, data in comparison.get('agencies', {}).items():
                print(f"\n  {agency}:")
                print(f"    - Violations: {data.get('violation_count', 0)}")
                if 'penalties' in data and data['penalties']:
                    penalties = data['penalties']
                    print(f"    - Total Penalties: ${penalties.get('total', 0):,.2f}")
                    print(f"    - Avg Penalty: ${penalties.get('average', 0):,.2f}")
        else:
            print("✗ No comparison data available")
    except Exception as e:
        print(f"✗ Error in comparison: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Violation Impact Analysis
    print(f"\n{'=' * 70}")
    print("TEST 4: Violation Impact Analysis")
    print(f"{'=' * 70}")
    print("Analyzing whether violations increased or reduced subsequent violations...")
    
    try:
        impact_analysis = analyzer.analyze_violation_impact(
            company_name,
            use_fuzzy=True
        )
        
        if 'error' not in impact_analysis:
            analyses = impact_analysis.get('impact_analysis', {}).get('analyses', [])
            summary = impact_analysis.get('impact_analysis', {}).get('summary', {})
            
            if analyses:
                print(f"✓ Impact analysis completed")
                
                if summary:
                    print(f"\nSummary:")
                    print(f"  - Total Analyses: {summary.get('total_analyses', 0)}")
                    print(f"  - Increased Violations: {summary.get('increased_violations', 0)}")
                    print(f"  - Reduced Violations: {summary.get('reduced_violations', 0)}")
                    print(f"  - No Change: {summary.get('no_change', 0)}")
                    print(f"  - Statistically Significant: {summary.get('statistically_significant', 0)}")
                    print(f"  - Avg Rate Change: {summary.get('avg_rate_change_pct', 0):.1f}%")
                
                print("\nDetailed Analyses:")
                for idx, analysis in enumerate(analyses[:3], 1):  # Show first 3
                    impact = analysis.get('impact', {})
                    analysis_type = analysis.get('analysis_type', 'violation')
                    
                    print(f"\n  Analysis {idx}: {analysis_type.replace('_', ' ').title()}")
                    print(f"    Impact: {impact.get('type', 'Unknown')}")
                    print(f"    Rate Change: {impact.get('rate_change_pct', 0):.1f}%")
                    print(f"    Strength: {impact.get('strength', 'Unknown')}")
                    print(f"    Significant: {impact.get('statistically_significant', False)} (p={impact.get('p_value', 1.0):.4f})")
                    
                    before = analysis.get('before_period', {})
                    after = analysis.get('after_period', {})
                    print(f"    Before: {before.get('violation_count', 0)} violations ({before.get('rate_per_year', 0):.2f}/year)")
                    print(f"    After: {after.get('violation_count', 0)} violations ({after.get('rate_per_year', 0):.2f}/year)")
            else:
                print("✗ No impact analyses available")
                print("  (May need more violations or sufficient time periods)")
        else:
            print(f"✗ Error: {impact_analysis.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"✗ Error in impact analysis: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Database Stats (if using database)
    print(f"\n{'=' * 70}")
    print("TEST 5: Database Statistics")
    print(f"{'=' * 70}")
    
    try:
        # Try to get database stats
        from src.database import get_db_manager
        db = get_db_manager()
        stats = db.get_stats()
        
        print("Database Status:")
        print(f"  Database: {stats.get('database_url', 'N/A')}")
        for table, info in stats.get('tables', {}).items():
            if info.get('exists'):
                print(f"  {table}: {info.get('row_count', 0):,} rows")
            else:
                print(f"  {table}: not found")
    except Exception as e:
        print(f"Note: Database stats not available: {e}")
    
    print(f"\n{'=' * 70}")
    print("TEST COMPLETE")
    print(f"{'=' * 70}")
    print("\nTo view results in the interactive dashboard:")
    print("  streamlit run app.py")
    print("\nThen navigate to the 'Company Comparison' tab and search for 'Amazon'")

if __name__ == "__main__":
    test_amazon_analysis()

