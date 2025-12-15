# Manual Download Steps for OSHA Data

Since the automatic URLs are not working, here's a step-by-step guide to manually download the data.

## Step 1: Visit DOL Enforcement Data Catalog

1. Open your browser
2. Go to: **https://enforcedata.dol.gov/views/data_catalogs.php**
3. This is the main DOL enforcement data portal

## Step 2: Find OSHA Data

1. On the data catalog page, look for:
   - "OSHA" section
   - "Occupational Safety and Health Administration"
   - Links to inspection, violation, or accident data

2. The page structure may have changed, so look for:
   - Data download links
   - CSV export options
   - "Download" buttons
   - Dataset listings

## Step 3: Download Files

You need these three files:
- **Inspection data** (may be named: `osha_inspection.csv`, `inspection_data.csv`, etc.)
- **Violation data** (may be named: `osha_violation.csv`, `violation_data.csv`, etc.)
- **Accident data** (may be named: `osha_accident.csv`, `accident_data.csv`, etc.)

## Step 4: Save to Data Directory

1. Create the data directory if it doesn't exist:
   ```bash
   mkdir -p /Users/sagehart/Downloads/osha-violation-analyzer/data
   ```

2. Save the downloaded files to:
   ```
   /Users/sagehart/Downloads/osha-violation-analyzer/data/
   ```

3. Rename files if needed to match expected names:
   - `osha_inspection.csv`
   - `osha_violation.csv`
   - `osha_accident.csv`

## Step 5: Verify

Run the status check:
```bash
python3 check_data_status.py
```

## Alternative: Use OSHA.gov Direct

If DOL site doesn't work:

1. Visit: **https://www.osha.gov/data**
2. Look for data download options
3. Check "Severe Injury Reports": https://www.osha.gov/severe-injury-reports
4. Check "Establishment-Specific Data": https://www.osha.gov/Establishment-Specific-Injury-and-Illness-Data

## What to Do If You Can't Find the Files

The data structure may have changed. Options:

1. **Contact DOL/OSHA**: They may have moved the data or require registration
2. **FOIA Request**: Submit a Freedom of Information Act request
3. **Use Available Data**: The system can work with partial data - download what's available

## After Download

Once files are in place:

```bash
# Check status
python3 check_data_status.py

# Test loading
python3 src/data_loader.py

# Test with Amazon
python3 scripts/test_amazon.py
```

