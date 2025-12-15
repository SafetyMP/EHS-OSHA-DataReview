#!/usr/bin/env python3
"""
Fast bulk hybrid year update script for violations table.
Uses optimized single-pass UPDATE with index management for maximum speed.

Strategy:
1. Drop year-related indexes (massive speed improvement)
2. Use single optimized UPDATE statement (fastest for SQLite)
3. Recreate indexes after update
4. Verify completion

This is the QUICKEST method - much faster than batching for SQLite.

Usage:
    python scripts/update_year_bulk.py
"""

import sys
from pathlib import Path
from sqlalchemy import text
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_db_manager


def drop_year_indexes(engine):
    """Drop indexes that include year column for faster updates."""
    indexes_to_drop = [
        'idx_violation_company_year',
        'idx_violation_state_year',
        'idx_violation_agency_year',
        'idx_violation_naics_year',
    ]
    
    print("Dropping year-related indexes for maximum update speed...")
    dropped = 0
    with engine.connect() as conn:
        for idx_name in indexes_to_drop:
            try:
                conn.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))
                dropped += 1
                print(f"  ✓ Dropped {idx_name}")
            except Exception as e:
                print(f"  ⚠ Could not drop {idx_name}: {e}")
        conn.commit()
    return dropped > 0


def recreate_year_indexes(engine):
    """Recreate indexes that include year column."""
    indexes_to_create = [
        ('idx_violation_company_year',
         "CREATE INDEX idx_violation_company_year ON violations(company_name_normalized, year)"),
        ('idx_violation_state_year',
         "CREATE INDEX idx_violation_state_year ON violations(site_state, year)"),
        ('idx_violation_agency_year',
         "CREATE INDEX idx_violation_agency_year ON violations(agency, year)"),
        ('idx_violation_naics_year',
         "CREATE INDEX idx_violation_naics_year ON violations(naics_code, year)"),
    ]
    
    print("\nRecreating year-related indexes...")
    with engine.connect() as conn:
        for idx_name, create_sql in indexes_to_create:
            try:
                conn.execute(text(create_sql))
                print(f"  ✓ Created {idx_name}")
            except Exception as e:
                print(f"  ⚠ Could not create {idx_name}: {e}")
        conn.commit()


def optimize_for_bulk_update(engine):
    """Optimize SQLite settings for bulk update performance."""
    print("Optimizing SQLite settings for bulk update...")
    optimizations = [
        "PRAGMA journal_mode = WAL",  # Write-Ahead Logging (already set, but ensure)
        "PRAGMA synchronous = NORMAL",  # Balance between speed and safety
        "PRAGMA cache_size = -64000",  # 64MB cache (negative = KB, 64000KB = 64MB)
        "PRAGMA temp_store = MEMORY",  # Use memory for temp tables
        "PRAGMA mmap_size = 268435456",  # 256MB memory-mapped I/O
    ]
    
    with engine.connect() as conn:
        for pragma in optimizations:
            try:
                conn.execute(text(pragma))
                print(f"  ✓ {pragma}")
            except Exception as e:
                print(f"  ⚠ {pragma}: {e}")
        conn.commit()


def update_year_bulk(engine):
    """
    Single-pass bulk UPDATE - fastest method for SQLite.
    
    Uses substr() which is much faster than strftime() and CAST().
    This is a single optimized UPDATE statement.
    """
    print("\nExecuting bulk UPDATE (single-pass, optimized)...")
    print("This may take a few minutes for 13+ million rows...")
    
    # Check how many rows need updating
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) as total
            FROM violations
            WHERE year IS NULL 
              AND violation_date IS NOT NULL
              AND length(violation_date) >= 4
        """))
        total_to_update = result.scalar()
    
    if total_to_update == 0:
        print("✓ All violations already have year set!")
        return 0
    
    print(f"  Rows to update: {total_to_update:,}")
    print("  Using optimized substr() method (fastest for string dates)")
    print()
    
    # Single optimized UPDATE - SQLite handles this efficiently with indexes dropped
    # Using substr() is much faster than strftime() for string-based dates
    update_sql = text("""
        UPDATE violations 
        SET year = CAST(substr(violation_date, 1, 4) AS INTEGER)
        WHERE year IS NULL 
          AND violation_date IS NOT NULL
          AND length(violation_date) >= 4
    """)
    
    start_time = time.time()
    
    try:
        with engine.connect() as conn:
            print("Executing UPDATE...")
            result = conn.execute(update_sql)
            rows_updated = result.rowcount
            conn.commit()
        
        elapsed = time.time() - start_time
        rate = rows_updated / elapsed if elapsed > 0 else 0
        
        print(f"\n✓ Successfully updated {rows_updated:,} violations")
        print(f"  Time: {elapsed:.1f} seconds ({elapsed/60:.2f} minutes)")
        print(f"  Rate: {rate:,.0f} rows/second")
        
        return rows_updated
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n✗ Error after {elapsed:.1f} seconds: {e}")
        import traceback
        traceback.print_exc()
        raise


def verify_update(engine):
    """Verify the update was successful."""
    print("\nVerifying update...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(year) as with_year,
                COUNT(*) - COUNT(year) as without_year,
                MIN(year) as min_year,
                MAX(year) as max_year,
                ROUND(100.0 * COUNT(year) / COUNT(*), 2) as pct_complete
            FROM violations
        """))
        row = result.fetchone()
        
        print(f"  Total violations: {row[0]:,}")
        print(f"  With year: {row[1]:,}")
        print(f"  Without year: {row[2]:,}")
        print(f"  Year range: {row[3]} - {row[4]}")
        print(f"  Completion: {row[5]}%")
        
        if row[2] > 0:
            # Check why some don't have year
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM violations 
                WHERE year IS NULL 
                  AND violation_date IS NOT NULL
                  AND length(violation_date) >= 4
            """))
            remaining = result.scalar()
            if remaining > 0:
                print(f"\n  ⚠ {remaining:,} rows still missing year (may need manual review)")
                # Sample some rows to see why
                result = conn.execute(text("""
                    SELECT violation_date, length(violation_date)
                    FROM violations 
                    WHERE year IS NULL 
                      AND violation_date IS NOT NULL
                      AND length(violation_date) >= 4
                    LIMIT 5
                """))
                samples = result.fetchall()
                print(f"  Sample problematic dates:")
                for date_val, length in samples:
                    print(f"    '{date_val}' (length: {length})")


def main():
    print("=" * 70)
    print("BULK HYBRID YEAR UPDATE - FASTEST METHOD")
    print("=" * 70)
    print()
    
    db = get_db_manager()
    engine = db.engine
    
    indexes_dropped = False
    try:
        # Step 1: Optimize SQLite settings
        optimize_for_bulk_update(engine)
        
        # Step 2: Drop indexes for maximum speed
        indexes_dropped = drop_year_indexes(engine)
        
        # Step 3: Bulk update (single-pass)
        rows_updated = update_year_bulk(engine)
        
        # Step 4: Recreate indexes
        if indexes_dropped:
            recreate_year_indexes(engine)
        
        # Step 5: Verify
        verify_update(engine)
        
        print("\n" + "=" * 70)
        print("BULK UPDATE COMPLETE!")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Update interrupted by user")
        if indexes_dropped:
            print("Recreating indexes...")
            recreate_year_indexes(engine)
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        if indexes_dropped:
            print("\n⚠ Attempting to recreate indexes...")
            recreate_year_indexes(engine)


if __name__ == "__main__":
    main()

