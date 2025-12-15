"""
Example: Using the Database Backend

This script demonstrates how to use the database-backed analyzer.
"""

from pathlib import Path
from src.analyzer_db import OSHAAnalyzerDB
from src.database import get_db_manager

# Example 1: Initialize and use database-backed analyzer
print("=" * 60)
print("Example 1: Using Database-Backed Analyzer")
print("=" * 60)

# Initialize analyzer (will use database if available)
analyzer = OSHAAnalyzerDB()

# Check if database has data
stats = analyzer.get_stats()
print(f"\nDatabase statistics:")
for table, info in stats['tables'].items():
    if info.get('exists'):
        print(f"  {table}: {info.get('row_count', 0):,} rows")
    else:
        print(f"  {table}: not found")

# Example queries (only work if data is loaded)
try:
    # Search violations
    print("\n" + "-" * 60)
    print("Searching violations for 2023 in California...")
    results = analyzer.search_violations(year=2023, state="CA", limit=5)
    print(f"Found {len(results)} violations")
    if not results.empty:
        print(f"Columns: {list(results.columns)}")
    
    # Top violations
    print("\n" + "-" * 60)
    print("Top 5 violations:")
    top = analyzer.top_violations(n=5)
    print(top.to_string())
    
    # Violations by state
    print("\n" + "-" * 60)
    print("Violations by state (top 5):")
    by_state = analyzer.violations_by_state().head(5)
    print(by_state.to_string())
    
except Exception as e:
    print(f"Error: {e}")
    print("\nTip: Run 'python -m src.db_migration' first to load data into database")

print("\n" + "=" * 60)
print("Example complete!")
print("=" * 60)

