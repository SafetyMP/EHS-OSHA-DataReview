"""
Test script to calculate average fine in 2007.

Usage:
    python scripts/test_average_fine_2007.py
"""

import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_average_fine_2007():
    """Calculate average fine/penalty in 2007."""
    print("=" * 70)
    print("TEST: Average Fine in 2007")
    print("=" * 70)
    print()
    
    try:
        data_dir = Path(__file__).parent.parent / "data"
        print(f"Data directory: {data_dir}")
        print()
        
        # Try database first
        db_path = data_dir / "compliance.db"
        use_database = False
        
        if db_path.exists():
            try:
                from src.database import get_db_manager
                db_manager = get_db_manager(data_dir=data_dir)
                session = db_manager.get_session()
                
                # Check if database has data
                result = session.execute(text("SELECT COUNT(*) FROM violations WHERE agency = 'OSHA'")).scalar()
                session.close()
                
                if result and result > 0:
                    use_database = True
                    print("✓ Using database backend")
                else:
                    print("⚠ Database exists but is empty, using CSV files")
            except Exception as e:
                print(f"⚠ Database error: {e}, using CSV files")
        
        if use_database:
            # Use database
            session = db_manager.get_session()
            
            try:
                print("Querying violations from 2007 using SQL...")
                
                # Query using raw SQL
                sql_query = text("""
                    SELECT 
                        COUNT(*) as total_count,
                        COUNT(CASE WHEN current_penalty IS NOT NULL AND current_penalty > 0 THEN 1 END) as violations_with_penalties,
                        AVG(CASE WHEN current_penalty > 0 THEN current_penalty END) as avg_penalty,
                        SUM(CASE WHEN current_penalty > 0 THEN current_penalty END) as total_penalty,
                        MIN(CASE WHEN current_penalty > 0 THEN current_penalty END) as min_penalty,
                        MAX(CASE WHEN current_penalty > 0 THEN current_penalty END) as max_penalty
                    FROM violations
                    WHERE agency = 'OSHA' 
                      AND year = 2007
                """)
                
                result = session.execute(sql_query).fetchone()
                
                total_count = result[0] if result else 0
                violations_with_penalties = result[1] if result else 0
                avg_penalty = result[2] if result else None
                total_penalty = result[3] if result else None
                min_penalty = result[4] if result else None
                max_penalty = result[5] if result else None
                
                print(f"Found {total_count:,} violations in 2007")
                
            finally:
                session.close()
        else:
            # Use CSV files
            from src.analyzer import OSHAAnalyzer
            print("✓ Using CSV-based analyzer")
            print("Loading data (this may take a moment)...")
            
            analyzer = OSHAAnalyzer()
            
            # Filter violations for 2007
            violations_df = analyzer.violations.copy()
            
            if violations_df.empty:
                print()
                print("⚠ No violation data loaded!")
                print("Please ensure CSV files are in the data/ directory")
                return
            
            if 'year' not in violations_df.columns:
                print()
                print("⚠ 'year' column not found in violations data")
                return
            
            violations_2007 = violations_df[violations_df['year'] == 2007]
            total_count = len(violations_2007)
            
            print(f"Found {total_count:,} violations in 2007")
            
            if total_count == 0:
                print()
                print("⚠ No violations found for 2007 in CSV files")
                available_years = sorted(violations_df['year'].dropna().unique())[-10:]
                print(f"Available years (last 10): {available_years}")
                return
            
            # Calculate statistics
            if 'current_penalty' in violations_2007.columns:
                violations_with_penalties_df = violations_2007[
                    (violations_2007['current_penalty'].notna()) & 
                    (violations_2007['current_penalty'] > 0)
                ]
                
                violations_with_penalties = len(violations_with_penalties_df)
                
                if violations_with_penalties > 0:
                    avg_penalty = violations_with_penalties_df['current_penalty'].mean()
                    total_penalty = violations_with_penalties_df['current_penalty'].sum()
                    min_penalty = violations_with_penalties_df['current_penalty'].min()
                    max_penalty = violations_with_penalties_df['current_penalty'].max()
                else:
                    avg_penalty = None
                    total_penalty = None
                    min_penalty = None
                    max_penalty = None
            else:
                avg_penalty = None
                total_penalty = None
                min_penalty = None
                max_penalty = None
                violations_with_penalties = 0
        
        if total_count == 0:
            print()
            print("⚠ No violations found for 2007")
            return
        
        # Display results
        print()
        print("=" * 70)
        print("RESULTS: 2007 Violation Penalties")
        print("=" * 70)
        print()
        
        if avg_penalty is not None:
            print(f"Total Violations:           {total_count:,}")
            print(f"Violations with Penalties: {violations_with_penalties:,}")
            print()
            print(f"Average Fine (Penalty):     ${avg_penalty:,.2f}")
            if total_penalty:
                print(f"Total Penalties:            ${total_penalty:,.2f}")
            if min_penalty:
                print(f"Minimum Penalty:            ${min_penalty:,.2f}")
            if max_penalty:
                print(f"Maximum Penalty:            ${max_penalty:,.2f}")
            print()
            print("=" * 70)
            print(f"✓ TEST COMPLETE: Average fine in 2007 = ${avg_penalty:,.2f}")
            print("=" * 70)
        else:
            print("⚠ No penalties found (all penalties are null or zero)")
            print()
            
    except ImportError as e:
        print("=" * 70)
        print("IMPORT ERROR")
        print("=" * 70)
        print(f"Error: {e}")
        print("\nPlease install dependencies first:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
        
    except Exception as e:
        print("=" * 70)
        print("ERROR")
        print("=" * 70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_average_fine_2007()
