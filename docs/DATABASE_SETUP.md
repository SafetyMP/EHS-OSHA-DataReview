# Database Backend Setup Guide

This guide explains how to use the new database backend for improved performance and scalability.

## Overview

The database backend provides:
- **Faster queries** - Indexed database queries instead of loading entire CSV files
- **Lower memory usage** - Query only what you need
- **Better scalability** - Handle larger datasets efficiently
- **Multi-agency support** - Unified database for all agencies

## Installation

The database backend uses SQLAlchemy and SQLite (by default). Dependencies are included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Initial Setup

### Step 1: Download CSV Data (if not already done)

First, ensure you have the CSV data files:

```bash
python src/data_loader.py
```

### Step 2: Migrate Data to Database

Run the migration script to load CSV data into the database:

```bash
python -m src.db_migration
```

This will:
- Create the database file at `data/compliance.db`
- Create all necessary tables
- Load data from CSV files into the database
- Show progress and statistics

**Options:**
- `--force-reload`: Delete existing data and reload from CSV
- `--tables TABLE [TABLE ...]`: Selective reload - specify which tables to load (e.g., `--tables accidents`)
- `--nrows N`: Limit to first N rows (for testing)
- `--stats`: Show database statistics without loading
- `--reset`: Drop all tables and recreate (destructive!)
- `--no-parallel`: Disable parallel processing (single-threaded)
- `--workers N`: Specify number of parallel workers

Example:
```bash
# Load all data
python -m src.db_migration

# Force reload (if data has changed)
python -m src.db_migration --force-reload

# Selective reload - reload only accidents table
python -m src.db_migration --force-reload --tables accidents

# Selective reload - reload multiple tables
python -m src.db_migration --force-reload --tables inspections violations

# Test with limited data
python -m src.db_migration --nrows 10000

# Check statistics
python -m src.db_migration --stats

# Use parallel processing with specific worker count
python -m src.db_migration --force-reload --workers 4
```

## Using the Database Backend

### In Code

#### Option 1: Use Database-Backed Analyzer

```python
from src.analyzer_db import OSHAAnalyzerDB

# Initialize with database backend
analyzer = OSHAAnalyzerDB()

# All methods work the same, but use database queries
results = analyzer.search_violations(year=2023, state="CA")
top_violations = analyzer.top_violations(n=10)
```

#### Option 2: Use Original CSV-Based Analyzer (backward compatible)

```python
from src.analyzer import OSHAAnalyzer

# Original CSV-based analyzer still works
analyzer = OSHAAnalyzer()
```

### In Streamlit App

The app automatically detects if a database exists and can use it. To force database usage:

1. Ensure database is initialized (`python -m src.db_migration`)
2. The app will prefer database if available

To modify the app to always use database:

```python
# In app.py, change:
from src.analyzer_db import OSHAAnalyzerDB as OSHAAnalyzer

@st.cache_resource
def load_analyzer():
    return OSHAAnalyzer()  # Now uses database
```

## Database Schema

### Tables

**inspections**
- `id` (primary key)
- `activity_nr` (unique, indexed)
- `estab_name` (indexed)
- `site_state` (indexed)
- `naics_code` (indexed)
- `open_date`, `close_case_date`
- `year` (indexed)
- `inspection_type`

**violations**
- `id` (primary key)
- `agency` (indexed) - "OSHA", "EPA", "MSHA", "FDA"
- `company_name` (indexed) - Original company name
- `company_name_normalized` (indexed) - Normalized for matching
- `activity_nr` (indexed) - Links to inspection
- `standard`, `viol_type`
- `current_penalty`, `initial_penalty`, `fta_penalty`
- `site_state` (indexed), `site_city`
- `naics_code` (indexed), `sic_code`
- `violation_date`, `year` (indexed)

**accidents**
- `id` (primary key)
- `accident_key` (unique, indexed)
- `activity_nr` (indexed)
- `estab_name` (indexed)
- `accident_date`, `year` (indexed)
- `description`, `fatality`, `injury_type`

### Indexes

Multiple indexes are created for fast queries:
- Company name (normalized and original)
- Agency, year, state
- NAICS codes
- Composite indexes for common query patterns

## Performance Comparison

| Operation | CSV-based | Database |
|-----------|-----------|----------|
| Initial load | Fast | Slower (one-time) |
| Search violations | Slow (loads all) | Fast (indexed query) |
| Top violations | Slow | Fast (aggregation) |
| Company search | Slow | Fast (indexed) |
| Memory usage | High (all in RAM) | Low (query only needed) |

## Using PostgreSQL (Optional)

To use PostgreSQL instead of SQLite:

1. Install PostgreSQL and create database
2. Install psycopg2: `pip install psycopg2-binary`
3. Set database URL:

```python
from src.database import DatabaseManager

db = DatabaseManager(
    database_url="postgresql://user:password@localhost/compliance_db"
)
```

Or set environment variable:
```bash
export DATABASE_URL="postgresql://user:password@localhost/compliance_db"
```

## Maintenance

### Update Data

When new CSV data is available:

```bash
# Re-download CSV files
python src/data_loader.py

# Reload all tables into database
python -m src.db_migration --force-reload

# Or reload only specific tables (faster)
python -m src.db_migration --force-reload --tables accidents
python -m src.db_migration --force-reload --tables violations inspections
```

**Selective Reload Benefits:**
- Faster updates when only one table changes
- Avoids unnecessary reloading of unchanged data
- Useful for incremental updates or fixing specific data issues

### Backup Database

```bash
# SQLite
cp data/compliance.db data/compliance.db.backup

# PostgreSQL
pg_dump compliance_db > backup.sql
```

### Check Database Size

```bash
python -m src.db_migration --stats
```

## Troubleshooting

### Database locked error
- Ensure no other processes are using the database
- Close all Streamlit sessions
- Restart the application

### Out of memory during migration
- Use `--nrows` to load data in chunks
- Process data in batches
- Consider using PostgreSQL for very large datasets

### Missing data after migration
- Check CSV files exist in `data/` directory
- Verify CSV files are not corrupted
- Check migration logs for errors
- Try `--force-reload` to re-import

## Migration from CSV to Database

The system maintains backward compatibility:
- Original `OSHAAnalyzer` class still works with CSV
- New `OSHAAnalyzerDB` uses database
- Both can coexist
- App can detect and use either

To fully migrate:
1. Run database migration
2. Update imports to use `analyzer_db` module
3. Test all functionality
4. Remove CSV files if desired (database is now source of truth)

## Quick Tips

**For faster initial loading:**
- Use database backend (recommended) - one-time 10-20 minute load, then instant startup
- Use parallel processing: `python -m src.db_migration --workers 4`
- Use selective reload for updates: `python -m src.db_migration --force-reload --tables accidents`

**For testing:**
- Use `--nrows 10000` to load sample data quickly
- Check progress with `--stats` flag

## Next Steps

- See `ENHANCEMENTS.md` for additional features
- Consider implementing incremental updates
- Add data validation and quality checks
- Set up automated backups

