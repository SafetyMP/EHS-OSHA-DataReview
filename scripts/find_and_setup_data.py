"""
Helper script to find downloaded OSHA data files and set them up correctly.
"""

import os
from pathlib import Path
import shutil
import zipfile

# Common locations where files might be
SEARCH_LOCATIONS = [
    Path.home() / "Downloads",
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path("/Users/sagehart/Downloads"),
    Path.cwd() / "data"
]

# File name patterns to look for
FILE_PATTERNS = {
    "inspection": [
        "*inspection*.csv",
        "*inspection*.zip",
        "*inspection*.CSV",
        "osha_inspection*"
    ],
    "violation": [
        "*violation*.csv",
        "*violation*.zip",
        "*violation*.CSV",
        "osha_violation*"
    ],
    "accident": [
        "*accident*.csv",
        "*accident*.zip",
        "*accident*.CSV",
        "osha_accident*"
    ]
}

TARGET_NAMES = {
    "inspection": "osha_inspection.csv",
    "violation": "osha_violation.csv",
    "accident": "osha_accident.csv"
}

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def find_files():
    """Find downloaded OSHA data files."""
    print("=" * 70)
    print("FINDING DOWNLOADED OSHA DATA FILES")
    print("=" * 70)
    print()
    
    found_files = {
        "inspection": [],
        "violation": [],
        "accident": []
    }
    
    print("Searching in common locations...")
    for location in SEARCH_LOCATIONS:
        if location.exists():
            print(f"  Checking: {location}")
            for data_type, patterns in FILE_PATTERNS.items():
                for pattern in patterns:
                    matches = list(location.glob(pattern))
                    for match in matches:
                        if match not in found_files[data_type]:
                            found_files[data_type].append(match)
    
    print()
    print("Found files:")
    print("-" * 70)
    
    for data_type, files in found_files.items():
        print(f"\n{data_type.upper()} files:")
        if files:
            for f in files:
                size_mb = f.stat().st_size / (1024 * 1024) if f.exists() else 0
                print(f"  ✓ {f} ({size_mb:.1f} MB)")
        else:
            print(f"  ✗ No {data_type} files found")
    
    return found_files


def setup_files(found_files):
    """Copy/rename files to correct location and names."""
    print()
    print("=" * 70)
    print("SETTING UP FILES")
    print("=" * 70)
    print()
    
    for data_type, files in found_files.items():
        target_name = TARGET_NAMES[data_type]
        target_path = DATA_DIR / target_name
        
        if target_path.exists():
            print(f"⚠ {target_name} already exists in data directory")
            response = input(f"  Overwrite? (y/n): ").strip().lower()
            if response != 'y':
                print(f"  Skipping {target_name}")
                continue
        
        if not files:
            print(f"✗ No {data_type} files to copy")
            continue
        
        # Use the largest file if multiple found
        source_file = max(files, key=lambda f: f.stat().st_size if f.exists() else 0)
        
        print(f"Copying {data_type} data...")
        print(f"  From: {source_file}")
        print(f"  To: {target_path}")
        
        try:
            # If it's a zip, extract first
            if source_file.suffix.lower() == '.zip':
                print(f"  Extracting ZIP file...")
                with zipfile.ZipFile(source_file, 'r') as z:
                    # Find CSV file in zip
                    csv_files = [f for f in z.namelist() if f.endswith('.csv')]
                    if csv_files:
                        # Extract the first CSV (usually there's one main file)
                        csv_name = csv_files[0]
                        with z.open(csv_name) as source, open(target_path, 'wb') as target:
                            target.write(source.read())
                        print(f"  ✓ Extracted {csv_name} to {target_name}")
                    else:
                        print(f"  ⚠ No CSV files found in ZIP")
                        # Extract all anyway
                        z.extractall(DATA_DIR)
            else:
                # Just copy the file
                shutil.copy2(source_file, target_path)
                print(f"  ✓ Copied to {target_name}")
            
            # Verify
            if target_path.exists():
                size_mb = target_path.stat().st_size / (1024 * 1024)
                print(f"  ✓ Verified: {size_mb:.1f} MB")
            else:
                print(f"  ✗ File not found after copy")
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print()


def main():
    """Main function."""
    print()
    
    # Find files
    found_files = find_files()
    
    # Check if any files were found
    total_found = sum(len(files) for files in found_files.values())
    if total_found == 0:
        print()
        print("=" * 70)
        print("NO FILES FOUND")
        print("=" * 70)
        print()
        print("Could not find OSHA data files in common locations.")
        print()
        print("Please tell me:")
        print("  1. Where did you download the files? (path)")
        print("  2. What are the file names?")
        print()
        print("Or manually copy files to:")
        print(f"  {DATA_DIR.absolute()}")
        print()
        print("Expected file names:")
        for name in TARGET_NAMES.values():
            print(f"  - {name}")
        return
    
    # Ask if user wants to set up files
    print()
    response = input("Would you like to copy/rename these files to the data directory? (y/n): ").strip().lower()
    
    if response == 'y':
        setup_files(found_files)
        
        # Final check
        print()
        print("=" * 70)
        print("FINAL STATUS")
        print("=" * 70)
        
        from src.data_loader import get_data_summary
        summary = get_data_summary()
        
        for name, info in summary.items():
            if info.get('status') == 'loaded':
                rows = info.get('rows', 0)
                print(f"✓ {name}: {rows:,} rows")
            else:
                print(f"✗ {name}: {info.get('status', 'unknown')}")
    else:
        print()
        print("Files not moved. You can manually copy them to:")
        print(f"  {DATA_DIR.absolute()}")
        print()
        print("Expected names:")
        for name in TARGET_NAMES.values():
            print(f"  - {name}")


if __name__ == "__main__":
    main()

