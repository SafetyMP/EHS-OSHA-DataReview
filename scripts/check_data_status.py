"""
Check data status and provide helpful information.
"""

from pathlib import Path
import os

DATA_DIR = Path(__file__).parent / "data"

def check_data_status():
    """Check what data files are available."""
    print("=" * 70)
    print("DATA STATUS CHECK")
    print("=" * 70)
    print()
    
    required_files = {
        "osha_inspection.csv": "Inspection data",
        "osha_violation.csv": "Violation data",
        "osha_accident.csv": "Accident data"
    }
    
    print(f"Data directory: {DATA_DIR.absolute()}")
    print(f"Directory exists: {DATA_DIR.exists()}")
    print()
    
    all_present = True
    for filename, description in required_files.items():
        filepath = DATA_DIR / filename
        exists = filepath.exists()
        status = "✓" if exists else "✗"
        
        if exists:
            size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"{status} {filename:25s} - {description:20s} ({size_mb:.1f} MB)")
        else:
            print(f"{status} {filename:25s} - {description:20s} (MISSING)")
            all_present = False
    
    print()
    
    # Check for zip files
    zip_files = list(DATA_DIR.glob("*.zip"))
    if zip_files:
        print("Found ZIP files (need to be extracted):")
        for zip_file in zip_files:
            size_mb = zip_file.stat().st_size / (1024 * 1024)
            print(f"  - {zip_file.name} ({size_mb:.1f} MB)")
        print()
        print("To extract ZIP files, run:")
        print("  unzip data/*.zip -d data/")
        print()
    
    # Summary
    print("=" * 70)
    if all_present:
        print("✓ All required data files are present!")
        print()
        print("Next steps:")
        print("  1. Test loading: python3 src/data_loader.py")
        print("  2. Migrate to database: python3 -m src.db_migration")
        print("  3. Test with Amazon: python3 test_amazon.py")
        print("  4. Launch dashboard: streamlit run app.py")
    else:
        print("✗ Some data files are missing")
        print()
        print("To download data:")
        print("  1. See DATA_DOWNLOAD_GUIDE.md for manual download instructions")
        print("  2. Visit: https://enforcedata.dol.gov/views/data_catalogs.php")
        print("  3. Download OSHA inspection, violation, and accident data")
        print("  4. Place CSV files in the 'data/' directory")
    print("=" * 70)

if __name__ == "__main__":
    check_data_status()

