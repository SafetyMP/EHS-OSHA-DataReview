"""
Combine split CSV files and set them up in the data directory.
"""

import pandas as pd
from pathlib import Path
import sys

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DOWNLOADS_DIR = Path.home() / "Downloads"

def combine_csv_files(source_dir, output_file, file_pattern="*.csv", skip_header_after_first=True):
    """Combine multiple CSV files into one."""
    print(f"Combining files from: {source_dir}")
    
    csv_files = sorted(source_dir.glob(file_pattern))
    if not csv_files:
        print(f"  ✗ No files found matching {file_pattern}")
        return False
    
    print(f"  Found {len(csv_files)} files to combine")
    
    # Read first file to get header
    print(f"  Reading {csv_files[0].name}...")
    try:
        df_first = pd.read_csv(csv_files[0], low_memory=False, nrows=0)  # Just header
        header = list(df_first.columns)
        print(f"  Columns: {len(header)}")
    except Exception as e:
        print(f"  ✗ Error reading first file: {e}")
        return False
    
    # Combine files using chunked reading to save memory
    print(f"  Combining files...")
    chunk_size = 100000
    total_rows = 0
    
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            # Write header
            first_file = True
            for i, csv_file in enumerate(csv_files):
                print(f"    Processing {csv_file.name} ({i+1}/{len(csv_files)})...", end=" ")
                
                try:
                    # Read in chunks
                    chunk_count = 0
                    for chunk in pd.read_csv(csv_file, low_memory=False, chunksize=chunk_size):
                        if first_file:
                            # Write header with first chunk
                            chunk.to_csv(outfile, index=False, header=True)
                            first_file = False
                        else:
                            # Skip header for subsequent files
                            chunk.to_csv(outfile, index=False, header=False)
                        chunk_count += 1
                        total_rows += len(chunk)
                    
                    print(f"✓ ({chunk_count} chunks, {total_rows:,} total rows so far)")
                except Exception as e:
                    print(f"✗ Error: {e}")
                    continue
        
        print(f"  ✓ Combined {len(csv_files)} files into {output_file.name}")
        print(f"  ✓ Total rows: {total_rows:,}")
        
        # Verify output file
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"  ✓ Output size: {file_size_mb:.1f} MB")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error combining files: {e}")
        return False


def main():
    """Main function."""
    print("=" * 70)
    print("COMBINING AND SETTING UP OSHA DATA FILES")
    print("=" * 70)
    print()
    
    # Inspection data
    print("1. Setting up INSPECTION data...")
    inspection_dir = DOWNLOADS_DIR / "osha_inspection_20251214"
    inspection_output = DATA_DIR / "osha_inspection.csv"
    
    if inspection_dir.exists():
        if combine_csv_files(inspection_dir, inspection_output):
            print(f"  ✓ Inspection data ready: {inspection_output}")
        else:
            print(f"  ✗ Failed to combine inspection data")
    else:
        print(f"  ✗ Directory not found: {inspection_dir}")
    print()
    
    # Violation data
    print("2. Setting up VIOLATION data...")
    violation_dir = DOWNLOADS_DIR / "osha_violation_20251214"
    violation_output = DATA_DIR / "osha_violation.csv"
    
    if violation_dir.exists():
        if combine_csv_files(violation_dir, violation_output):
            print(f"  ✓ Violation data ready: {violation_output}")
        else:
            print(f"  ✗ Failed to combine violation data")
    else:
        print(f"  ✗ Directory not found: {violation_dir}")
    print()
    
    # Accident data - check multiple locations
    print("3. Setting up ACCIDENT data...")
    accident_sources = [
        DOWNLOADS_DIR / "osha_accident_20251214",
        DOWNLOADS_DIR / "msha_accident.csv",  # MSHA accident (different agency but might work)
    ]
    
    accident_output = DATA_DIR / "osha_accident.csv"
    accident_found = False
    
    for source in accident_sources:
        if source.exists():
            if source.is_file():
                # Single file, just copy
                print(f"  Found: {source.name}")
                print(f"  Copying to {accident_output.name}...")
                import shutil
                shutil.copy2(source, accident_output)
                size_mb = accident_output.stat().st_size / (1024 * 1024)
                print(f"  ✓ Copied ({size_mb:.1f} MB)")
                accident_found = True
                break
            elif source.is_dir():
                # Directory with multiple files, combine
                if combine_csv_files(source, accident_output):
                    print(f"  ✓ Accident data ready: {accident_output}")
                    accident_found = True
                    break
    
    if not accident_found:
        print(f"  ⚠ Accident data not found (optional)")
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    from src.data_loader import get_data_summary
    summary = get_data_summary()
    
    for name, info in summary.items():
        if info.get('status') == 'loaded':
            rows = info.get('rows', 0)
            print(f"✓ {name}: {rows:,} rows")
        else:
            print(f"✗ {name}: {info.get('status', 'unknown')}")
    
    print()
    print("Next steps:")
    print("  1. Test loading: python3 src/data_loader.py")
    print("  2. (Optional) Migrate to database: python3 -m src.db_migration")
    print("  3. Test with Amazon: python3 test_amazon.py")
    print("  4. Launch dashboard: streamlit run app.py")


if __name__ == "__main__":
    main()

