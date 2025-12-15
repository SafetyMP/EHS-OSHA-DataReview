"""
OSHA Data Loader
Downloads and preprocesses OSHA enforcement data from the DOL Data Catalog.
"""

import os
import requests
import zipfile
import pandas as pd
from pathlib import Path
from datetime import datetime

# DOL Enforcement Data URLs
DATA_URLS = {
    "inspection": "https://enfxfr.dol.gov/data_catalog/OSHA/osha_inspection.csv.zip",
    "violation": "https://enfxfr.dol.gov/data_catalog/OSHA/osha_violation.csv.zip", 
    "accident": "https://enfxfr.dol.gov/data_catalog/OSHA/osha_accident.csv.zip",
}

DATA_DIR = Path(__file__).parent.parent / "data"


def download_file(url: str, filename: str) -> Path:
    """Download a file from URL to data directory."""
    DATA_DIR.mkdir(exist_ok=True)
    filepath = DATA_DIR / filename
    
    print(f"Downloading {filename}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(filepath, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return filepath


def extract_zip(zip_path: Path) -> Path:
    """Extract a zip file and return path to extracted CSV."""
    print(f"Extracting {zip_path.name}...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(DATA_DIR)
    
    csv_name = zip_path.stem  # Remove .zip extension
    os.remove(zip_path)
    return DATA_DIR / csv_name


def load_inspections(nrows: int = None) -> pd.DataFrame:
    """Load and preprocess inspection data."""
    filepath = DATA_DIR / "osha_inspection.csv"
    
    if not filepath.exists():
        zip_path = download_file(DATA_URLS["inspection"], "osha_inspection.csv.zip")
        extract_zip(zip_path)
    
    print("Loading inspections...")
    df = pd.read_csv(filepath, low_memory=False, nrows=nrows)
    
    # Parse dates
    date_cols = ["open_date", "close_case_date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    
    # Extract year for easier filtering
    if "open_date" in df.columns:
        df["year"] = df["open_date"].dt.year
    
    return df


def load_violations(nrows: int = None) -> pd.DataFrame:
    """Load and preprocess violation data."""
    filepath = DATA_DIR / "osha_violation.csv"
    
    if not filepath.exists():
        zip_path = download_file(DATA_URLS["violation"], "osha_violation.csv.zip")
        extract_zip(zip_path)
    
    print("Loading violations...")
    df = pd.read_csv(filepath, low_memory=False, nrows=nrows)
    
    # Clean penalty columns
    penalty_cols = ["initial_penalty", "current_penalty", "fta_penalty"]
    for col in penalty_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    
    return df


def load_accidents(nrows: int = None) -> pd.DataFrame:
    """Load and preprocess accident data."""
    filepath = DATA_DIR / "osha_accident.csv"
    
    if not filepath.exists():
        zip_path = download_file(DATA_URLS["accident"], "osha_accident.csv.zip")
        extract_zip(zip_path)
    
    print("Loading accidents...")
    df = pd.read_csv(filepath, low_memory=False, nrows=nrows)
    
    return df


def get_data_summary() -> dict:
    """Return summary statistics about loaded data."""
    summary = {}
    
    # Map dataset names to their file names
    file_map = {
        "inspections": "osha_inspection.csv",
        "violations": "osha_violation.csv",
        "accidents": "osha_accident.csv"
    }
    
    for name, loader in [("inspections", load_inspections), 
                          ("violations", load_violations),
                          ("accidents", load_accidents)]:
        try:
            filepath = DATA_DIR / file_map[name]
            
            if filepath.exists():
                # Get full row count
                with open(filepath, "r") as f:
                    row_count = sum(1 for _ in f) - 1  # Subtract header
                summary[name] = {"status": "loaded", "rows": row_count}
            else:
                summary[name] = {"status": "not downloaded"}
        except Exception as e:
            summary[name] = {"status": "error", "message": str(e)}
    
    return summary


if __name__ == "__main__":
    print("OSHA Data Loader")
    print("=" * 50)
    
    # Download all datasets
    print("\nDownloading OSHA enforcement data...")
    print("This may take a few minutes on first run.\n")
    
    inspections = load_inspections()
    print(f"✓ Loaded {len(inspections):,} inspections")
    
    violations = load_violations()
    print(f"✓ Loaded {len(violations):,} violations")
    
    accidents = load_accidents()
    print(f"✓ Loaded {len(accidents):,} accidents")
    
    print("\n" + "=" * 50)
    print("Data download complete! Run 'streamlit run app.py' to launch dashboard.")
