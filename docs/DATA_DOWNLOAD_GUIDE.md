# OSHA Data Download Guide

The automatic download URLs have changed. Here's how to get the data manually.

## Option 1: DOL Enforcement Data Catalog (Recommended)

1. **Visit the DOL Data Catalog:**
   - Go to: https://enforcedata.dol.gov/views/data_catalogs.php

2. **Find OSHA Data:**
   - Look for "OSHA" or "Occupational Safety and Health Administration" section
   - Browse available datasets

3. **Download the following files:**
   - `osha_inspection.csv` (or `.csv.zip`)
   - `osha_violation.csv` (or `.csv.zip`)
   - `osha_accident.csv` (or `.csv.zip`)

4. **Place files in the data directory:**
   ```bash
   # Navigate to your project directory
   cd /Users/sagehart/Downloads/osha-violation-analyzer
   
   # Place downloaded files here:
   data/osha_inspection.csv
   data/osha_violation.csv
   data/osha_accident.csv
   ```

5. **Extract if needed:**
   If you downloaded `.zip` files, extract them to the `data/` directory.

## Option 2: OSHA.gov Direct Downloads

### Severe Injury Reports
- Visit: https://www.osha.gov/severe-injury-reports
- Click "Download the full SIR data set"
- Note: This is a different dataset but may be useful

### Establishment-Specific Data
- Visit: https://www.osha.gov/Establishment-Specific-Injury-and-Illness-Data
- Download available datasets
- Note: Format may differ from what the code expects

### Inspection Search
- Visit: https://www.osha.gov/data
- Search by establishment name, NAICS code, or inspection number
- Data may need to be exported/processed differently

## Option 3: FOIA Request

If data is not publicly available:
1. Visit: https://www.osha.gov/foia/
2. Submit a FOIA request for inspection, violation, and accident data
3. Specify you want CSV format if possible

## Option 4: Sample Data for Testing

If you want to test the system without full data:

1. **Create sample data files:**
   ```python
   # You can create minimal CSV files with just headers
   # The system will work with empty or minimal data
   ```

2. **Use the system with existing data:**
   If you have any OSHA data already, you can:
   - Rename columns to match expected format
   - Place in the `data/` directory
   - The system should adapt

## Expected File Format

The code expects CSV files with these columns (at minimum):

### osha_inspection.csv
- `activity_nr` - Inspection activity number (unique identifier)
- `estab_name` - Establishment name
- `site_state` - State code (e.g., "CA", "NY")
- `naics_code` - NAICS industry code
- `open_date` - Inspection open date
- `close_case_date` - Case close date (optional)
- `inspection_type` - Type of inspection (optional)
- `year` - Year (auto-generated from open_date if not present)

### osha_violation.csv
- `activity_nr` - Links to inspection
- `standard` - OSHA standard number (e.g., "1910.134")
- `viol_type` - Violation type
- `description` - Violation description (optional)
- `initial_penalty` - Initial penalty amount
- `current_penalty` - Current penalty amount
- `fta_penalty` - Failure to abate penalty (optional)

### osha_accident.csv
- `accident_key` - Accident identifier (unique)
- `activity_nr` - Links to inspection
- `estab_name` - Establishment name
- `site_state` - State code
- `accident_date` - Date of accident
- `description` - Accident description (optional)
- `fatality` - Whether fatality occurred (optional)

## Verifying Data

After downloading, verify the data:

```bash
# Check if files exist
ls -lh data/*.csv

# Check file sizes (should be substantial, not empty)
# Inspection data: typically 100+ MB
# Violation data: typically 200+ MB
# Accident data: typically 50+ MB

# Check first few lines
head -5 data/osha_inspection.csv
head -5 data/osha_violation.csv
```

## Testing After Download

Once you have the data files:

```bash
# Test loading
python3 src/data_loader.py

# If successful, you should see:
# ✓ Loaded X inspections
# ✓ Loaded Y violations
# ✓ Loaded Z accidents
```

## Next Steps

1. After downloading data, you can:
   ```bash
   # Optionally migrate to database for better performance
   python3 -m src.db_migration
   
   # Then test with Amazon
   python3 scripts/test_amazon.py
   
   # Or launch the dashboard
   streamlit run app.py
   ```

## Troubleshooting

### Files not found?
- Make sure files are in `data/` directory (not `data/data/`)
- Check file names are exactly: `osha_inspection.csv`, etc.
- Make sure files are not empty

### Import errors?
- Make sure pandas is installed: `pip install pandas`

### Column errors?
- The code is flexible and will work with partial data
- Missing optional columns are okay
- Required: `activity_nr` for violations to link to inspections

### Still can't find data?
- The DOL may have changed their data structure
- Consider contacting DOL or OSHA directly
- Check if there's an API available instead of direct downloads

