"""
Helper script to download OSHA data with alternative URLs and manual download instructions.
"""

import requests
from pathlib import Path
import zipfile

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Alternative URLs to try
ALTERNATIVE_URLS = {
    "inspection": [
        "https://enfxfr.dol.gov/data_catalog/OSHA/osha_inspection.csv.zip",
        "https://enforcedata.dol.gov/data_catalog/OSHA/osha_inspection.csv.zip",
        "https://www.dol.gov/sites/dolgov/files/OPA/newsreleases/osha_inspection.csv.zip",
    ],
    "violation": [
        "https://enfxfr.dol.gov/data_catalog/OSHA/osha_violation.csv.zip",
        "https://enforcedata.dol.gov/data_catalog/OSHA/osha_violation.csv.zip",
    ],
    "accident": [
        "https://enfxfr.dol.gov/data_catalog/OSHA/osha_accident.csv.zip",
        "https://enforcedata.dol.gov/data_catalog/OSHA/osha_accident.csv.zip",
    ]
}


def try_download(url: str, filename: str) -> bool:
    """Try to download a file, return True if successful."""
    try:
        print(f"  Trying: {url}")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        filepath = DATA_DIR / filename
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"  ✓ Successfully downloaded {filename}")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def download_with_alternatives():
    """Try to download data using alternative URLs."""
    print("=" * 70)
    print("OSHA Data Download Helper")
    print("=" * 70)
    print()
    
    print("Attempting to download OSHA data from alternative sources...")
    print()
    
    results = {}
    
    for data_type, urls in ALTERNATIVE_URLS.items():
        print(f"Downloading {data_type} data...")
        filename = f"osha_{data_type}.csv.zip"
        success = False
        
        for url in urls:
            if try_download(url, filename):
                success = True
                results[data_type] = filename
                break
        
        if not success:
            print(f"  ✗ Could not download {data_type} data from any URL")
            results[data_type] = None
        
        print()
    
    # Try to extract if any downloads succeeded
    if any(results.values()):
        print("Extracting downloaded files...")
        for data_type, filename in results.items():
            if filename:
                try:
                    zip_path = DATA_DIR / filename
                    csv_name = zip_path.stem  # Remove .zip
                    csv_path = DATA_DIR / csv_name
                    
                    if not csv_path.exists():
                        print(f"  Extracting {filename}...")
                        with zipfile.ZipFile(zip_path, "r") as z:
                            z.extractall(DATA_DIR)
                        print(f"  ✓ Extracted to {csv_name}")
                        
                        # Remove zip file to save space
                        zip_path.unlink()
                        print(f"  ✓ Removed {filename}")
                    else:
                        print(f"  ✓ {csv_name} already exists")
                except Exception as e:
                    print(f"  ✗ Error extracting {filename}: {e}")
        print()
    
    # Summary
    print("=" * 70)
    print("Download Summary")
    print("=" * 70)
    
    for data_type, filename in results.items():
        csv_name = f"osha_{data_type}.csv"
        csv_path = DATA_DIR / csv_name
        if csv_path.exists():
            size_mb = csv_path.stat().st_size / (1024 * 1024)
            print(f"✓ {csv_name}: {size_mb:.1f} MB")
        else:
            print(f"✗ {csv_name}: Not available")
    
    print()
    
    # Manual download instructions
    if not all(results.values()):
        print("=" * 70)
        print("MANUAL DOWNLOAD INSTRUCTIONS")
        print("=" * 70)
        print()
        print("Some data files could not be downloaded automatically.")
        print("Please download manually from:")
        print()
        print("1. Visit: https://enforcedata.dol.gov/views/data_catalogs.php")
        print("2. Navigate to OSHA data catalog")
        print("3. Download the following files:")
        print("   - osha_inspection.csv (or .zip)")
        print("   - osha_violation.csv (or .zip)")
        print("   - osha_accident.csv (or .zip)")
        print("4. Place them in the 'data/' directory")
        print()
        print(f"Data directory: {DATA_DIR.absolute()}")
        print()
        print("Alternative: Use OSHA's Severe Injury Reports data:")
        print("  https://www.osha.gov/severe-injury-reports")
        print()


if __name__ == "__main__":
    download_with_alternatives()

