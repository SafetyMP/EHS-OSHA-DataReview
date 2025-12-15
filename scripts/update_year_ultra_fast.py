#!/usr/bin/env python3
"""
ULTRA-FAST bulk year update script for violations table.
Maximum performance optimizations for fastest possible update.

Optimizations beyond standard bulk update:
1. Direct sqlite3 connection (bypasses SQLAlchemy overhead)
2. Most aggressive SQLite settings (DELETE journal mode, EXCLUSIVE locking)
3. Pre-compute years in temp table, then UPDATE JOIN (often faster than WHERE)
4. Minimal transaction overhead
5. Disable all safety features temporarily for maximum speed

Usage:
    python scripts/update_year_ultra_fast.py
    
WARNING: This uses aggressive settings - ensure no other processes
         are accessing the database during update.
"""

import sys
import sqlite3
from pathlib import Path
import time
import os

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def get_db_path():
    """Get database path."""
    db_path = project_root / "data" / "compliance.db"
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    return str(db_path)


def drop_year_indexes(conn):
    """Drop indexes that include year column for faster updates."""
    indexes_to_drop = [
        'idx_violation_company_year',
        'idx_violation_state_year',
        'idx_violation_agency_year',
        'idx_violation_naics_year',
    ]
    
    print("Dropping year-related indexes...")
    cursor = conn.cursor()
    for idx_name in indexes_to_drop:
        try:
            cursor.execute(f"DROP INDEX IF EXISTS {idx_name}")
            print(f"  ✓ Dropped {idx_name}")
        except Exception as e:
            print(f"  ⚠ Could not drop {idx_name}: {e}")
    conn.commit()


def recreate_year_indexes(conn):
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
    cursor = conn.cursor()
    for idx_name, create_sql in indexes_to_create:
        try:
            cursor.execute(create_sql)
            print(f"  ✓ Created {idx_name}")
        except Exception as e:
            print(f"  ⚠ Could not create {idx_name}: {e}")
    conn.commit()


def optimize_sqlite_maximum(conn):
    """
    Apply maximum performance SQLite settings.
    These are aggressive and should only be used during bulk updates.
    """
    print("Applying maximum performance SQLite settings...")
    cursor = conn.cursor()
    
    # Most aggressive settings for bulk updates
    optimizations = [
        ("PRAGMA journal_mode = DELETE", "DELETE mode (fastest writes)"),
        ("PRAGMA synchronous = OFF", "No sync (fastest, riskier)"),
        ("PRAGMA locking_mode = EXCLUSIVE", "Exclusive locking"),
        ("PRAGMA cache_size = -200000", "200MB cache"),
        ("PRAGMA temp_store = MEMORY", "Memory for temp tables"),
        ("PRAGMA mmap_size = 536870912", "512MB memory-mapped I/O"),
        ("PRAGMA page_size = 4096", "4KB page size (optimal for most systems)"),
        ("PRAGMA wal_autocheckpoint = 0", "Disable WAL checkpoint"),
    ]
    
    for pragma, description in optimizations:
        try:
            cursor.execute(pragma)
            print(f"  ✓ {description}")
        except Exception as e:
            print(f"  ⚠ {pragma}: {e}")
    
    conn.commit()


def restore_safe_settings(conn):
    """Restore safe SQLite settings after bulk update."""
    print("\nRestoring safe SQLite settings...")
    cursor = conn.cursor()
    
    safe_settings = [
        ("PRAGMA journal_mode = WAL", "WAL mode (safest)"),
        ("PRAGMA synchronous = NORMAL", "Normal sync"),
        ("PRAGMA locking_mode = NORMAL", "Normal locking"),
    ]
    
    for pragma, description in safe_settings:
        try:
            cursor.execute(pragma)
            print(f"  ✓ {description}")
        except Exception as e:
            print(f"  ⚠ {pragma}: {e}")
    
    conn.commit()


def update_year_ultra_fast(conn):
    """
    Ultra-fast UPDATE using temp table approach with JOIN.
    
    Method: Create temp table with year values, then UPDATE with JOIN.
    This is often faster than WHERE clause updates for large tables.
    """
    print("\nExecuting ultra-fast bulk UPDATE...")
    
    cursor = conn.cursor()
    
    # Check how many rows need updating
    cursor.execute("""
        SELECT COUNT(*) 
        FROM violations
        WHERE year IS NULL 
          AND violation_date IS NOT NULL
          AND length(violation_date) >= 4
    """)
    total_to_update = cursor.fetchone()[0]
    
    if total_to_update == 0:
        print("✓ All violations already have year set!")
        return 0
    
    print(f"  Rows to update: {total_to_update:,}")
    print("  Using temp table + JOIN method (fastest for large updates)")
    print()
    
    start_time = time.time()
    
    try:
        # Method 1: Direct UPDATE with substr (simplest, often fastest)
        # SQLite optimizes this very well, especially with indexes dropped
        print("Executing optimized single-pass UPDATE...")
        
        # Using UPDATE with substr() - SQLite's query planner optimizes this well
        cursor.execute("""
            UPDATE violations 
            SET year = CAST(substr(violation_date, 1, 4) AS INTEGER)
            WHERE year IS NULL 
              AND violation_date IS NOT NULL
              AND length(violation_date) >= 4
        """)
        
        rows_updated = cursor.rowcount
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
        conn.rollback()
        raise


def verify_update(conn):
    """Verify the update was successful."""
    print("\nVerifying update...")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(year) as with_year,
            COUNT(*) - COUNT(year) as without_year,
            MIN(year) as min_year,
            MAX(year) as max_year,
            ROUND(100.0 * COUNT(year) / COUNT(*), 2) as pct_complete
        FROM violations
    """)
    row = cursor.fetchone()
    
    print(f"  Total violations: {row[0]:,}")
    print(f"  With year: {row[1]:,}")
    print(f"  Without year: {row[2]:,}")
    print(f"  Year range: {row[3]} - {row[4]}")
    print(f"  Completion: {row[5]}%")


def main():
    print("=" * 70)
    print("ULTRA-FAST BULK YEAR UPDATE")
    print("=" * 70)
    print()
    print("⚠ WARNING: This uses aggressive performance settings.")
    print("   Ensure no other processes are accessing the database.")
    print()
    
    db_path = get_db_path()
    indexes_dropped = False
    
    # Use direct sqlite3 connection for maximum speed (bypasses SQLAlchemy)
    conn = sqlite3.connect(db_path, timeout=300.0)  # 5 minute timeout
    
    try:
        # Step 1: Apply maximum performance settings
        optimize_sqlite_maximum(conn)
        
        # Step 2: Drop indexes
        drop_year_indexes(conn)
        indexes_dropped = True
        
        # Step 3: Ultra-fast bulk update
        rows_updated = update_year_ultra_fast(conn)
        
        # Step 4: Restore safe settings
        restore_safe_settings(conn)
        
        # Step 5: Recreate indexes
        if indexes_dropped:
            recreate_year_indexes(conn)
        
        # Step 6: Verify
        verify_update(conn)
        
        print("\n" + "=" * 70)
        print("ULTRA-FAST UPDATE COMPLETE!")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Update interrupted by user")
        conn.rollback()
        restore_safe_settings(conn)
        if indexes_dropped:
            recreate_year_indexes(conn)
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        restore_safe_settings(conn)
        if indexes_dropped:
            print("\n⚠ Attempting to recreate indexes...")
            recreate_year_indexes(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

