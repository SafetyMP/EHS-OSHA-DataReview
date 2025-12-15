#!/usr/bin/env python3
"""
Fast batched year update script for violations table.
Updates year column from violation_date using efficient batched approach.

This is MUCH faster than a single UPDATE statement:
- Drops indexes temporarily
- Updates in batches with transactions
- Uses substr() instead of strftime() for speed
- Recreates indexes after completion

Usage:
    python scripts/update_year_batched.py
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
    
    print("Dropping year-related indexes for faster updates...")
    with engine.connect() as conn:
        for idx_name in indexes_to_drop:
            try:
                conn.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))
                print(f"  ✓ Dropped {idx_name}")
            except Exception as e:
                print(f"  ⚠ Could not drop {idx_name}: {e}")
        conn.commit()


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


def update_year_batched(engine, batch_size=100000):
    """
    Update year column in batches for maximum speed.
    
    Uses substr() which is much faster than strftime() for string dates.
    """
    print(f"\nUpdating year column in batches of {batch_size:,} rows...")
    print("Using substr() for maximum speed (much faster than strftime())")
    
    # SQLite-specific: Extract first 4 characters (year) from date string
    # violation_date format: "YYYY-MM-DD HH:MM:SS.ffffff"
    update_sql = text("""
        UPDATE violations 
        SET year = CAST(substr(violation_date, 1, 4) AS INTEGER)
        WHERE year IS NULL 
          AND violation_date IS NOT NULL
          AND length(violation_date) >= 4
          AND id >= :start_id
          AND id < :end_id
    """)
    
    # Get total count
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) as total,
                   MIN(id) as min_id,
                   MAX(id) as max_id
            FROM violations
            WHERE year IS NULL 
              AND violation_date IS NOT NULL
              AND length(violation_date) >= 4
        """))
        row = result.fetchone()
        total_to_update = row[0]
        min_id = row[1]
        max_id = row[2]
    
    if total_to_update == 0:
        print("✓ All violations already have year set!")
        return
    
    print(f"  Total to update: {total_to_update:,}")
    print(f"  ID range: {min_id:,} to {max_id:,}")
    print()
    
    start_time = time.time()
    total_updated = 0
    batch_num = 0
    
    # Process in batches
    current_start = min_id
    
    try:
        while current_start <= max_id:
            batch_num += 1
            batch_end = min(current_start + batch_size, max_id + 1)
            
            with engine.connect() as conn:
                result = conn.execute(update_sql, {
                    'start_id': current_start,
                    'end_id': batch_end
                })
                rows_updated = result.rowcount
                conn.commit()
            
            total_updated += rows_updated
            elapsed = time.time() - start_time
            rate = total_updated / elapsed if elapsed > 0 else 0
            remaining = total_to_update - total_updated
            eta = remaining / rate if rate > 0 else 0
            pct = (total_updated / total_to_update * 100) if total_to_update > 0 else 0
            
            print(f"Batch {batch_num}: Updated {rows_updated:,} rows | "
                  f"Total: {total_updated:,}/{total_to_update:,} ({pct:.1f}%) | "
                  f"Rate: {rate:,.0f} rows/sec | ETA: {eta/60:.1f} min")
            
            # Move to next batch
            current_start = batch_end
            
            # Check if done
            if rows_updated == 0 or total_updated >= total_to_update:
                break
        
        total_time = time.time() - start_time
        print(f"\n✓ Successfully updated {total_updated:,} violations in {total_time/60:.1f} minutes")
        print(f"  Average rate: {total_updated/total_time:,.0f} rows/second")
        
    except Exception as e:
        print(f"\n✗ Error during batch update: {e}")
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


def main():
    print("=" * 70)
    print("FAST BATCHED YEAR UPDATE")
    print("=" * 70)
    print()
    
    db = get_db_manager()
    engine = db.engine
    
    try:
        # Step 1: Drop indexes for speed
        drop_year_indexes(engine)
        
        # Step 2: Update in batches
        update_year_batched(engine, batch_size=100000)
        
        # Step 3: Recreate indexes
        recreate_year_indexes(engine)
        
        # Step 4: Verify
        verify_update(engine)
        
        print("\n" + "=" * 70)
        print("UPDATE COMPLETE!")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Update interrupted by user")
        print("Indexes may need to be recreated manually")
        recreate_year_indexes(engine)
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\n⚠ Attempting to recreate indexes...")
        recreate_year_indexes(engine)


if __name__ == "__main__":
    main()

