"""
Database-backed Data Loader
Loads data from CSVs into database and provides database queries.
Optimized with streaming chunked loading for large datasets.

This module provides:
- Streaming chunked loading for memory efficiency
- Native bulk import methods (SQLite executemany, PostgreSQL COPY)
- Parallel processing for inspections
- Multi-format support (OSHA standard, OSHA fatality reports, MSHA)
- Selective table reloading
"""

import pandas as pd
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text
import logging
import re
import time
import csv
import subprocess
import tempfile
import multiprocessing as mp
from functools import partial

from .database import DatabaseManager, Inspection, Violation, Accident, get_db_manager
from .data_loader import load_inspections as load_csv_inspections
from .data_loader import load_violations as load_csv_violations
from .data_loader import load_accidents as load_csv_accidents
from .data_loader import DATA_DIR
from .agency_base import AgencyDataLoader

logger = logging.getLogger(__name__)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def _normalize_company_name_vectorized(series: pd.Series) -> pd.Series:
    """
    Vectorized company name normalization (much faster than row-by-row).
    
    This is a vectorized version of CompanyNameMatcher.normalize_company_name()
    optimized for bulk processing.
    """
    # Handle NaN values
    mask = series.notna() & (series != "")
    result = pd.Series(index=series.index, dtype="object")
    
    if not mask.any():
        return result.fillna("")
    
    # Convert to string and uppercase
    normalized = series[mask].astype(str).str.upper().str.strip()
    
    # Remove common suffixes (vectorized)
    suffixes = [
        " INC", " LLC", " CORP", " CORPORATION", " LP", " LTD", 
        " COMPANY", " CO", " L.L.C.", " INC.", " CORP.", " CO.",
        " PLC", " PLLC", " LLP", " PA", " PC", " P.C.",
        " LLC.", " INCORPORATED", " LIMITED", " ASSOCIATES",
        " ASSOCIATION", " GROUP", " HOLDINGS", " HOLDING"
    ]
    
    for suffix in suffixes:
        normalized = normalized.str.replace(suffix + "$", "", regex=True).str.strip()
    
    # Remove punctuation and special characters
    normalized = normalized.str.replace(r'[^\w\s]', ' ', regex=True)
    
    # Normalize whitespace
    normalized = normalized.str.replace(r'\s+', ' ', regex=True).str.strip()
    
    # Remove common words
    def remove_common_words(name):
        if pd.isna(name) or not name:
            return ""
        words = name.split()
        common_words = {"THE", "A", "AN"}
        words = [w for w in words if w not in common_words]
        return " ".join(words)
    
    normalized = normalized.apply(remove_common_words)
    
    result[mask] = normalized
    return result.fillna("")


# ============================================================================
# DATABASE OPTIMIZATION FUNCTIONS
# ============================================================================

def _optimize_sqlite_for_bulk_load(engine):
    """Optimize SQLite settings for faster bulk inserts."""
    if "sqlite" in str(engine.url):
        with engine.connect() as conn:
            # Disable synchronous writes (faster, but less safe - acceptable for bulk loads)
            conn.execute(sa_text("PRAGMA synchronous = OFF"))
            # Increase cache size (default is 2MB, use 64MB)
            conn.execute(sa_text("PRAGMA cache_size = -64000"))
            # Use WAL mode for better concurrency
            conn.execute(sa_text("PRAGMA journal_mode = WAL"))
            # Increase page size for better performance
            conn.execute(sa_text("PRAGMA page_size = 4096"))
            conn.commit()
            logger.info("SQLite optimized for bulk loading")


# ============================================================================
# BULK INSERT FUNCTIONS
# ============================================================================

def _bulk_insert_dataframe(engine, table_name: str, df: pd.DataFrame, use_native: bool = True):
    """
    Bulk insert DataFrame using native bulk import methods when available.
    Falls back to pandas to_sql if native methods aren't available.
    
    Args:
        engine: SQLAlchemy engine
        table_name: Target table name
        df: DataFrame to insert (must match table columns)
        use_native: If True, try native bulk import first
    """
    if df.empty:
        return
    
    database_url = str(engine.url)
    
    # Try native bulk import for SQLite
    if use_native and "sqlite" in database_url:
        try:
            _bulk_insert_sqlite_executemany(engine, table_name, df)
            return
        except Exception as e:
            logger.warning(f"Native SQLite bulk insert failed, falling back to pandas: {e}")
    
    # Try native bulk import for PostgreSQL
    if use_native and ("postgresql" in database_url or "postgres" in database_url):
        try:
            _bulk_insert_postgresql_copy(engine, table_name, df)
            return
        except Exception as e:
            logger.warning(f"Native PostgreSQL bulk insert failed, falling back to pandas: {e}")
    
    # Fallback to pandas to_sql
    df.to_sql(
        table_name,
        engine,
        if_exists='append',
        index=False,
        method='multi',
        chunksize=100  # Safe for SQLite variable limit
    )


def _bulk_insert_sqlite_executemany(engine, table_name: str, df: pd.DataFrame):
    """
    Use SQLite's executemany for fast bulk inserts.
    This is 5-10x faster than pandas to_sql because it uses prepared statements.
    """
    if df.empty:
        return
    
    # Get column names in order
    columns = list(df.columns)
    
    # Build INSERT statement
    placeholders = ','.join(['?' for _ in columns])
    column_names = ','.join([f'"{col}"' for col in columns])  # Quote column names
    insert_sql = f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})'
    
    # Convert DataFrame to list of tuples, handling NaN values and data types
    # Replace NaN with None for SQL NULL
    # Convert Timestamp objects to strings for SQLite compatibility
    data_rows = []
    for _, row in df.iterrows():
        # Convert row to tuple, replacing NaN/NaT with None
        row_values = []
        for val in row:
            if pd.isna(val):
                row_values.append(None)
            else:
                # Handle datetime/Timestamp types
                try:
                    # Check if it's a Timestamp or datetime-like
                    if isinstance(val, pd.Timestamp):
                        row_values.append(val.strftime('%Y-%m-%d %H:%M:%S.%f'))
                    elif hasattr(val, 'to_pydatetime'):  # pandas datetime64
                        dt = val.to_pydatetime()
                        row_values.append(dt.strftime('%Y-%m-%d %H:%M:%S.%f'))
                    elif hasattr(val, 'strftime'):  # datetime objects
                        row_values.append(val.strftime('%Y-%m-%d %H:%M:%S.%f'))
                    elif hasattr(val, 'item'):  # numpy/pandas scalar types
                        # Convert numpy/pandas scalars to Python native types
                        converted = val.item()
                        # Check if converted value is datetime-like
                        if hasattr(converted, 'strftime'):
                            row_values.append(converted.strftime('%Y-%m-%d %H:%M:%S.%f'))
                        else:
                            row_values.append(converted)
                    else:
                        row_values.append(val)
                except (ValueError, AttributeError, TypeError):
                    # Fallback: convert to string
                    row_values.append(str(val) if val is not None else None)
        data_rows.append(tuple(row_values))
    
    # Use raw connection for executemany
    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        # Insert in smaller batches for SQLite to avoid lock issues
        # Smaller batches = more frequent commits = less lock contention
        batch_size = 1000 if "sqlite" in str(engine.url) else 10000
        
        for i in range(0, len(data_rows), batch_size):
            batch = data_rows[i:i + batch_size]
            try:
                cursor.executemany(insert_sql, batch)
                raw_conn.commit()  # Commit after each batch for SQLite
            except Exception as batch_error:
                # If batch fails, try individual inserts for this batch
                if "database is locked" in str(batch_error):
                    logger.debug(f"Database locked on batch, retrying individually")
                    raw_conn.rollback()
                    for row in batch:
                        try:
                            cursor.execute(insert_sql, row)
                            raw_conn.commit()
                        except Exception as row_error:
                            logger.debug(f"Failed to insert row: {row_error}")
                            raw_conn.rollback()
                else:
                    # Other errors - re-raise
                    raw_conn.rollback()
                    raise
    except Exception as e:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()


def _bulk_insert_postgresql_copy(engine, table_name: str, df: pd.DataFrame):
    """
    Use PostgreSQL COPY command for fastest bulk loading.
    This is 10-20x faster than INSERT statements.
    """
    try:
        import io
    except ImportError:
        raise ImportError("io module required for PostgreSQL COPY")
    
    if df.empty:
        return
    
    # Get column names
    columns = list(df.columns)
    column_names = ','.join([f'"{col}"' for col in columns])
    
    # Create in-memory CSV buffer
    csv_buffer = io.StringIO()
    
    # Write DataFrame to CSV buffer
    # PostgreSQL COPY expects NULL to be represented as \N or empty string
    # We'll use empty string for NULL values
    df_clean = df.copy()
    # Replace NaN/NaT with None, then convert to empty string for COPY
    df_clean = df_clean.where(pd.notnull(df_clean), None)
    
    # Write to CSV with proper NULL handling
    for _, row in df_clean.iterrows():
        row_values = []
        for val in row:
            if val is None or pd.isna(val):
                row_values.append('')  # Empty string for NULL
            else:
                # Convert to string, handle special characters
                val_str = str(val)
                # Escape quotes and backslashes for CSV
                if '"' in val_str or ',' in val_str or '\n' in val_str:
                    val_str = '"' + val_str.replace('"', '""') + '"'
                row_values.append(val_str)
        csv_buffer.write(','.join(row_values) + '\n')
    
    csv_buffer.seek(0)
    
    # Use raw connection for COPY
    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        
        # Prepare COPY command
        copy_sql = f"""
            COPY "{table_name}" ({column_names})
            FROM STDIN
            WITH (FORMAT CSV, DELIMITER ',', QUOTE '"', ESCAPE '\\', NULL '')
        """
        
        # Execute COPY
        cursor.copy_expert(copy_sql, csv_buffer)
        raw_conn.commit()
        cursor.close()
    except Exception as e:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()


# ============================================================================
# INDEX MANAGEMENT FUNCTIONS
# ============================================================================

def _count_csv_rows(csv_path: Path) -> int:
    """Count total rows in CSV file (for progress tracking)."""
    try:
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Read first line to check if it's a header
            first_line = f.readline()
            if not first_line:
                return 0
            
            # Count remaining lines
            count = sum(1 for _ in f)
            return count
    except Exception as e:
        logger.warning(f"Could not count CSV rows: {e}")
        return 0


def _drop_table_indexes(engine, table_name: str):
    """Drop indexes on a table for faster bulk inserts."""
    indexes_map = {
        'inspections': [
            'idx_inspection_state_year',
            'idx_inspection_naics',
        ],
        'violations': [
            'idx_violation_agency_company',
            'idx_violation_company_year',
            'idx_violation_state_year',
            'idx_violation_agency_year',
            'idx_violation_penalty',
            'idx_violation_standard_agency',
            'idx_violation_naics_year',
        ],
        'accidents': [],  # Accidents use single-column indexes defined in model
    }
    
    indexes = indexes_map.get(table_name, [])
    if not indexes:
        return
    
    logger.info(f"Dropping {len(indexes)} indexes on {table_name} for faster inserts...")
    with engine.connect() as conn:
        for idx_name in indexes:
            try:
                conn.execute(sa_text(f"DROP INDEX IF EXISTS {idx_name}"))
            except Exception as e:
                logger.debug(f"Could not drop index {idx_name}: {e}")
        conn.commit()


def _create_table_indexes(engine, table_name: str):
    """Recreate indexes on a table after bulk load."""
    indexes_map = {
        'inspections': [
            ('idx_inspection_state_year', 
             "CREATE INDEX idx_inspection_state_year ON inspections(site_state, year)"),
            ('idx_inspection_naics',
             "CREATE INDEX idx_inspection_naics ON inspections(naics_code, year)"),
        ],
        'violations': [
            ('idx_violation_agency_company',
             "CREATE INDEX idx_violation_agency_company ON violations(agency, company_name_normalized)"),
            ('idx_violation_company_year',
             "CREATE INDEX idx_violation_company_year ON violations(company_name_normalized, year)"),
            ('idx_violation_state_year',
             "CREATE INDEX idx_violation_state_year ON violations(site_state, year)"),
            ('idx_violation_agency_year',
             "CREATE INDEX idx_violation_agency_year ON violations(agency, year)"),
            ('idx_violation_penalty',
             "CREATE INDEX idx_violation_penalty ON violations(current_penalty)"),
            ('idx_violation_standard_agency',
             "CREATE INDEX idx_violation_standard_agency ON violations(standard, agency)"),
            ('idx_violation_naics_year',
             "CREATE INDEX idx_violation_naics_year ON violations(naics_code, year)"),
        ],
        'accidents': [],  # Accidents indexes are created automatically by SQLAlchemy
    }
    
    indexes = indexes_map.get(table_name, [])
    if not indexes:
        return
    
    logger.info(f"Creating {len(indexes)} indexes on {table_name} (this may take a few minutes)...")
    start_time = time.time()
    
    with engine.connect() as conn:
        for idx_name, idx_sql in indexes:
            try:
                logger.debug(f"Creating index {idx_name}...")
                conn.execute(sa_text(idx_sql))
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not create index {idx_name}: {e}")
    
    elapsed = time.time() - start_time
    logger.info(f"Indexes created in {elapsed/60:.1f} minutes")


# ============================================================================
# PARALLEL PROCESSING FUNCTIONS
# ============================================================================

def _process_inspection_chunk_static(chunk_df: pd.DataFrame) -> pd.DataFrame:
    """Static version of inspection chunk processing (for parallel workers)."""
    insert_df = pd.DataFrame()
    insert_df['activity_nr'] = chunk_df['activity_nr'].astype(str).str.strip() if 'activity_nr' in chunk_df.columns else ""
    insert_df['estab_name'] = chunk_df['estab_name'].astype(str).str[:500] if 'estab_name' in chunk_df.columns else None
    insert_df['site_state'] = chunk_df['site_state'].astype(str).str.upper().str[:2] if 'site_state' in chunk_df.columns else None
    insert_df['naics_code'] = chunk_df['naics_code'].astype(str).str[:10] if 'naics_code' in chunk_df.columns else None
    insert_df['open_date'] = pd.to_datetime(chunk_df['open_date'], errors='coerce') if 'open_date' in chunk_df.columns else None
    insert_df['close_case_date'] = pd.to_datetime(chunk_df['close_case_date'], errors='coerce') if 'close_case_date' in chunk_df.columns else None
    insert_df['year'] = pd.to_numeric(chunk_df['year'], errors='coerce').astype('Int64') if 'year' in chunk_df.columns else None
    if 'year' not in chunk_df.columns and 'open_date' in insert_df.columns:
        insert_df['year'] = insert_df['open_date'].dt.year if insert_df['open_date'].notna().any() else None
    insert_df['inspection_type'] = chunk_df['inspection_type'].astype(str).str[:100] if 'inspection_type' in chunk_df.columns else None
    
    # Filter out rows with empty activity_nr
    insert_df = insert_df[insert_df['activity_nr'].str.strip().astype(bool)]
    insert_df = insert_df.replace('', None)
    
    return insert_df


def _parallel_worker_inspections(args):
    """
    Worker function for parallel inspection loading.
    Processes a chunk of CSV data and inserts into database.
    """
    start_row, end_row, csv_path, database_url, data_dir = args
    
    # Create own database connection for this worker
    from .database import DatabaseManager
    db = DatabaseManager(database_url=database_url, data_dir=data_dir)
    
    # Optimize SQLite for this worker
    _optimize_sqlite_for_bulk_load(db.engine)
    
    # For SQLite, add timeout and retry logic
    is_sqlite = "sqlite" in database_url
    if is_sqlite:
        import time
        max_retries = 3
        retry_delay = 0.1  # 100ms delay between retries
    
    try:
        rows_processed = 0
        
        # Read CSV in chunks, processing only our assigned range
        chunk_size = 50000
        current_row = 0
        
        for chunk_df in pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False):
            chunk_start = current_row
            chunk_end = current_row + len(chunk_df)
            current_row = chunk_end
            
            # Skip chunks before our range
            if chunk_end <= start_row:
                continue
            
            # Stop if we've passed our range
            if chunk_start >= end_row:
                break
            
            # Trim chunk to our range
            if chunk_start < start_row:
                skip_in_chunk = start_row - chunk_start
                chunk_df = chunk_df.iloc[skip_in_chunk:]
            
            if chunk_start + len(chunk_df) > end_row:
                take_rows = end_row - (chunk_start + (start_row - chunk_start if chunk_start < start_row else 0))
                chunk_df = chunk_df.iloc[:take_rows]
            
            # Process and insert
            processed = _process_inspection_chunk_static(chunk_df)
            
            if not processed.empty:
                # For SQLite, retry on lock errors
                if is_sqlite:
                    for attempt in range(max_retries):
                        try:
                            _bulk_insert_dataframe(db.engine, 'inspections', processed, use_native=True)
                            rows_processed += len(processed)
                            break
                        except Exception as e:
                            if "database is locked" in str(e) and attempt < max_retries - 1:
                                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                                continue
                            else:
                                # Fall back to pandas to_sql on final retry or other errors
                                logger.warning(f"Native insert failed, using pandas fallback: {e}")
                                _bulk_insert_dataframe(db.engine, 'inspections', processed, use_native=False)
                                rows_processed += len(processed)
                                break
                else:
                    # PostgreSQL - no retry needed
                    _bulk_insert_dataframe(db.engine, 'inspections', processed, use_native=True)
                    rows_processed += len(processed)
        
        return rows_processed
    except Exception as e:
        logger.error(f"Worker error processing rows {start_row}-{end_row}: {e}")
        return 0
    finally:
        db.close()


# ============================================================================
# DATABASE DATA LOADER CLASS
# ============================================================================

class DatabaseDataLoader:
    """Load data from CSV files into database and query from database."""
    
    def __init__(self, data_dir: Optional[Path] = None, database_url: Optional[str] = None):
        """Initialize database data loader."""
        self.data_dir = data_dir or Path(__file__).parent.parent / "data"
        self.db = get_db_manager(database_url=database_url, data_dir=self.data_dir)
    
    def load_inspections_to_db(self, nrows: Optional[int] = None, force_reload: bool = False, 
                                use_streaming: bool = True, chunk_size: int = 50000,
                                use_parallel: bool = False, num_workers: Optional[int] = None):
        """
        Load inspections from CSV into database (optimized streaming version).
        
        Args:
            nrows: Limit number of rows to load (None = all)
            force_reload: If True, delete existing records and reload
            use_streaming: If True, use streaming chunks (recommended for large files)
            chunk_size: Size of chunks for streaming (default: 50000)
            use_parallel: If True, use parallel processing (multi-core)
            num_workers: Number of parallel workers (default: auto-detect)
        """
        # Check if data already exists
        existing_count = self.db.get_table_row_count("inspections")
        if existing_count > 0 and not force_reload:
            logger.info(f"Inspections table already has {existing_count} records. Use force_reload=True to reload.")
            return
        
        # Get CSV file path
        csv_path = DATA_DIR / "osha_inspection.csv"
        if not csv_path.exists():
            # Try to download if not exists
            logger.info("CSV file not found, attempting to download...")
            load_csv_inspections(nrows=1)  # This will download if needed
            if not csv_path.exists():
                logger.error(f"Inspection CSV file not found at {csv_path}")
                return
        
        # Optimize SQLite for bulk loading
        _optimize_sqlite_for_bulk_load(self.db.engine)
        
        session = self.db.get_session()
        try:
            # Delete existing records if force_reload
            if force_reload and existing_count > 0:
                logger.info(f"Deleting {existing_count} existing inspection records...")
                session.query(Inspection).delete()
                session.commit()
            
            # Drop indexes for faster inserts
            _drop_table_indexes(self.db.engine, 'inspections')
            
            if use_parallel and use_streaming:
                # Use parallel processing (requires streaming)
                if num_workers is None:
                    num_workers = min(mp.cpu_count(), 8)  # Cap at 8 workers
                logger.info(f"Using parallel processing with {num_workers} workers")
                self._load_inspections_parallel(csv_path, nrows, num_workers)
            elif use_streaming:
                self._load_inspections_streaming(csv_path, nrows, chunk_size)
            else:
                # Fallback to original method for small datasets
                logger.info("Loading inspections from CSV (non-streaming mode)...")
                df = load_csv_inspections(nrows=nrows)
                if not df.empty:
                    self._process_and_insert_inspections(df, session)
            
            # Recreate indexes
            _create_table_indexes(self.db.engine, 'inspections')
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error loading inspections: {e}")
            raise
        finally:
            session.close()
    
    def _load_inspections_streaming(self, csv_path: Path, nrows: Optional[int], chunk_size: int):
        """Load inspections using streaming chunks."""
        logger.info(f"Loading inspections from {csv_path.name} using streaming chunks...")
        
        # Get total row count for progress tracking
        total_rows = _count_csv_rows(csv_path)
        if nrows:
            total_rows = min(total_rows, nrows)
        logger.info(f"Total rows to load: {total_rows:,}")
        
        rows_loaded = 0
        start_time = time.time()
        seen_activity_nrs = set()  # For duplicate detection
        duplicates_removed = 0
        
        # Stream CSV in chunks
        for chunk_num, chunk_df in enumerate(
            pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False, nrows=nrows)
        ):
            # Remove duplicates within chunk and across chunks
            initial_chunk_size = len(chunk_df)
            chunk_df = chunk_df[~chunk_df['activity_nr'].isin(seen_activity_nrs)]
            if 'activity_nr' in chunk_df.columns:
                chunk_df = chunk_df.drop_duplicates(subset=['activity_nr'], keep='first')
                seen_activity_nrs.update(chunk_df['activity_nr'].astype(str))
            duplicates_removed += initial_chunk_size - len(chunk_df)
            
            if chunk_df.empty:
                continue
            
            # Process and insert chunk
            processed = self._process_inspection_chunk(chunk_df)
            if not processed.empty:
                # Use native bulk import (executemany for SQLite, COPY for PostgreSQL)
                _bulk_insert_dataframe(self.db.engine, 'inspections', processed, use_native=True)
            
            rows_loaded += len(processed)
            
            # Progress logging
            elapsed = time.time() - start_time
            if elapsed > 0:
                rate = rows_loaded / elapsed
                remaining = (total_rows - rows_loaded) / rate if rate > 0 else 0
                pct = (rows_loaded / total_rows * 100) if total_rows > 0 else 0
                logger.info(
                    f"Chunk {chunk_num + 1}: {rows_loaded:,}/{total_rows:,} rows "
                    f"({pct:.1f}%) | Rate: {rate:.0f} rows/sec | ETA: {remaining/60:.1f} min"
                )
        
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed:,} duplicate inspection records")
        
        total_time = time.time() - start_time
        logger.info(f"Successfully loaded {rows_loaded:,} inspections in {total_time/60:.1f} minutes")
    
    def _load_inspections_parallel(self, csv_path: Path, nrows: Optional[int], num_workers: int):
        """Load inspections using parallel processing."""
        logger.info(f"Loading inspections from {csv_path.name} using {num_workers} parallel workers...")
        
        # Get total row count
        total_rows = _count_csv_rows(csv_path)
        if nrows:
            total_rows = min(total_rows, nrows)
        logger.info(f"Total rows to load: {total_rows:,}")
        
        # Calculate chunk boundaries for each worker
        chunk_size = max(total_rows // num_workers, 10000)  # Minimum 10K rows per worker
        chunk_boundaries = []
        for i in range(num_workers):
            start_row = i * chunk_size
            end_row = min((i + 1) * chunk_size, total_rows) if i < num_workers - 1 else total_rows
            if start_row < total_rows:
                chunk_boundaries.append((start_row, end_row))
        
        logger.info(f"Split into {len(chunk_boundaries)} chunks for parallel processing")
        
        # Prepare arguments for workers
        database_url = str(self.db.engine.url)
        worker_args = [
            (start, end, csv_path, database_url, self.data_dir)
            for start, end in chunk_boundaries
        ]
        
        # Process in parallel
        start_time = time.time()
        with mp.Pool(num_workers) as pool:
            results = pool.map(_parallel_worker_inspections, worker_args)
        
        # Sum results
        total_loaded = sum(results)
        total_time = time.time() - start_time
        logger.info(f"Successfully loaded {total_loaded:,} inspections in {total_time/60:.1f} minutes using {num_workers} workers")
    
    def _process_inspection_chunk(self, chunk_df: pd.DataFrame) -> pd.DataFrame:
        """Process a chunk of inspection data."""
        insert_df = pd.DataFrame()
        insert_df['activity_nr'] = chunk_df['activity_nr'].astype(str).str.strip() if 'activity_nr' in chunk_df.columns else ""
        insert_df['estab_name'] = chunk_df['estab_name'].astype(str).str[:500] if 'estab_name' in chunk_df.columns else None
        insert_df['site_state'] = chunk_df['site_state'].astype(str).str.upper().str[:2] if 'site_state' in chunk_df.columns else None
        insert_df['naics_code'] = chunk_df['naics_code'].astype(str).str[:10] if 'naics_code' in chunk_df.columns else None
        insert_df['open_date'] = pd.to_datetime(chunk_df['open_date'], errors='coerce') if 'open_date' in chunk_df.columns else None
        insert_df['close_case_date'] = pd.to_datetime(chunk_df['close_case_date'], errors='coerce') if 'close_case_date' in chunk_df.columns else None
        insert_df['year'] = pd.to_numeric(chunk_df['year'], errors='coerce').astype('Int64') if 'year' in chunk_df.columns else None
        if 'year' not in chunk_df.columns and 'open_date' in insert_df.columns:
            insert_df['year'] = insert_df['open_date'].dt.year if insert_df['open_date'].notna().any() else None
        insert_df['inspection_type'] = chunk_df['inspection_type'].astype(str).str[:100] if 'inspection_type' in chunk_df.columns else None
        
        # Filter out rows with empty activity_nr
        insert_df = insert_df[insert_df['activity_nr'].str.strip().astype(bool)]
        insert_df = insert_df.replace('', None)
        
        return insert_df
    
    def _process_and_insert_inspections(self, df: pd.DataFrame, session: Session):
        """Process and insert inspections (non-streaming fallback)."""
        # Remove duplicates
        initial_count = len(df)
        df = df.drop_duplicates(subset=['activity_nr'], keep='first')
        duplicates_removed = initial_count - len(df)
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate inspection records")
        
        processed = self._process_inspection_chunk(df)
        if not processed.empty:
            _bulk_insert_dataframe(self.db.engine, 'inspections', processed, use_native=True)
            logger.info(f"Successfully loaded {len(processed)} inspections")
    
    def load_violations_to_db(self, nrows: Optional[int] = None, force_reload: bool = False, 
                              agency: str = "OSHA", use_streaming: bool = True, chunk_size: int = 50000):
        """
        Load violations from CSV into database (optimized streaming version).
        
        Args:
            nrows: Limit number of rows to load (None = all)
            force_reload: If True, delete existing records for this agency and reload
            agency: Agency name (default: "OSHA")
            use_streaming: If True, use streaming chunks (recommended for large files)
            chunk_size: Size of chunks for streaming (default: 50000)
        """
        if agency != "OSHA":
            logger.warning(f"No CSV loader implemented for {agency}")
            return
        
        session = self.db.get_session()
        try:
            # Check if data already exists for this agency
            if not force_reload:
                existing_count = session.query(Violation).filter(Violation.agency == agency).count()
                if existing_count > 0:
                    logger.info(f"Violations table already has {existing_count} {agency} records. Use force_reload=True to reload.")
                    return
            
            # Get CSV file paths
            violations_csv = DATA_DIR / "osha_violation.csv"
            inspections_csv = DATA_DIR / "osha_inspection.csv"
            
            if not violations_csv.exists():
                logger.info("Violation CSV file not found, attempting to download...")
                load_csv_violations(nrows=1)
                if not violations_csv.exists():
                    logger.error(f"Violation CSV file not found at {violations_csv}")
                    return
            
            # Load inspections for merging (we'll load this in chunks too if needed)
            # For now, load a sample to get the merge columns
            logger.info("Loading inspection data for merging...")
            inspections_df = None
            if inspections_csv.exists():
                # Load inspections in chunks and create a lookup dict
                inspections_lookup = {}
                for chunk in pd.read_csv(inspections_csv, chunksize=100000, low_memory=False, nrows=nrows):
                    inspection_cols = ["activity_nr", "estab_name", "site_state", "naics_code", "open_date", "year"]
                    available_cols = [c for c in inspection_cols if c in chunk.columns]
                    for _, row in chunk[available_cols].iterrows():
                        activity_nr = str(row.get('activity_nr', ''))
                        if activity_nr:
                            inspections_lookup[activity_nr] = {
                                col: row.get(col) for col in available_cols if col != 'activity_nr'
                            }
                logger.info(f"Loaded {len(inspections_lookup):,} inspection records for merging")
            else:
                logger.warning("Inspection CSV not found, skipping merge")
            
            # Optimize SQLite for bulk loading
            _optimize_sqlite_for_bulk_load(self.db.engine)
            
            # Delete existing records for this agency if force_reload
            if force_reload:
                existing_count = session.query(Violation).filter(Violation.agency == agency).count()
                if existing_count > 0:
                    logger.info(f"Deleting {existing_count} existing {agency} violation records...")
                    session.query(Violation).filter(Violation.agency == agency).delete()
                    session.commit()
            
            # Drop indexes for faster inserts
            _drop_table_indexes(self.db.engine, 'violations')
            
            if use_streaming:
                self._load_violations_streaming(violations_csv, inspections_lookup, nrows, chunk_size, agency)
            else:
                # Fallback to original method
                logger.info(f"Loading {agency} violations from CSV (non-streaming mode)...")
                violations_df = load_csv_violations(nrows=nrows)
                inspections_df = load_csv_inspections(nrows=nrows)
                
                if not violations_df.empty:
                    if not inspections_df.empty and "activity_nr" in violations_df.columns and "activity_nr" in inspections_df.columns:
                        inspection_cols = ["activity_nr", "estab_name", "site_state", "naics_code", "open_date", "year"]
                        available_cols = [c for c in inspection_cols if c in inspections_df.columns]
                        violations_df = violations_df.merge(
                            inspections_df[available_cols],
                            on="activity_nr",
                            how="left"
                        )
                    self._process_and_insert_violations(violations_df, agency)
            
            # Recreate indexes
            _create_table_indexes(self.db.engine, 'violations')
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error loading violations: {e}")
            raise
        finally:
            session.close()
    
    def _load_violations_streaming(self, csv_path: Path, inspections_lookup: dict, 
                                  nrows: Optional[int], chunk_size: int, agency: str):
        """Load violations using streaming chunks."""
        logger.info(f"Loading {agency} violations from {csv_path.name} using streaming chunks...")
        
        # Get total row count for progress tracking
        total_rows = _count_csv_rows(csv_path)
        if nrows:
            total_rows = min(total_rows, nrows)
        logger.info(f"Total rows to load: {total_rows:,}")
        
        rows_loaded = 0
        start_time = time.time()
        
        # Stream CSV in chunks
        for chunk_num, chunk_df in enumerate(
            pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False, nrows=nrows)
        ):
            # Merge with inspections lookup
            if inspections_lookup and 'activity_nr' in chunk_df.columns:
                chunk_df['estab_name'] = chunk_df['activity_nr'].astype(str).map(
                    lambda x: inspections_lookup.get(x, {}).get('estab_name')
                )
                chunk_df['site_state'] = chunk_df['activity_nr'].astype(str).map(
                    lambda x: inspections_lookup.get(x, {}).get('site_state')
                )
                chunk_df['naics_code'] = chunk_df['activity_nr'].astype(str).map(
                    lambda x: inspections_lookup.get(x, {}).get('naics_code')
                )
                chunk_df['open_date'] = chunk_df['activity_nr'].astype(str).map(
                    lambda x: inspections_lookup.get(x, {}).get('open_date')
                )
                chunk_df['year'] = chunk_df['activity_nr'].astype(str).map(
                    lambda x: inspections_lookup.get(x, {}).get('year')
                )
            
            # Process and insert chunk
            processed = self._process_violation_chunk(chunk_df, agency)
            if not processed.empty:
                # Use native bulk import (executemany for SQLite, COPY for PostgreSQL)
                _bulk_insert_dataframe(self.db.engine, 'violations', processed, use_native=True)
            
            rows_loaded += len(processed)
            
            # Progress logging
            elapsed = time.time() - start_time
            if elapsed > 0:
                rate = rows_loaded / elapsed
                remaining = (total_rows - rows_loaded) / rate if rate > 0 else 0
                pct = (rows_loaded / total_rows * 100) if total_rows > 0 else 0
                logger.info(
                    f"Chunk {chunk_num + 1}: {rows_loaded:,}/{total_rows:,} rows "
                    f"({pct:.1f}%) | Rate: {rate:.0f} rows/sec | ETA: {remaining/60:.1f} min"
                )
        
        total_time = time.time() - start_time
        logger.info(f"Successfully loaded {rows_loaded:,} {agency} violations in {total_time/60:.1f} minutes")
    
    def _process_violation_chunk(self, chunk_df: pd.DataFrame, agency: str) -> pd.DataFrame:
        """Process a chunk of violation data."""
        # Create DataFrame with agency column first (ensure it matches chunk length)
        insert_df = pd.DataFrame(index=chunk_df.index)
        insert_df['agency'] = agency  # This will broadcast to all rows
        
        # Company name and normalized name (vectorized)
        if 'estab_name' in chunk_df.columns:
            company_names = chunk_df['estab_name'].fillna('').astype(str)
            insert_df['company_name'] = company_names.str[:500].replace('', None)
            # Vectorized normalization (much faster!)
            insert_df['company_name_normalized'] = _normalize_company_name_vectorized(company_names).str[:500].replace('', None)
        else:
            insert_df['company_name'] = None
            insert_df['company_name_normalized'] = None
        
        # Other fields with vectorized operations
        insert_df['activity_nr'] = chunk_df['activity_nr'].astype(str).str[:50] if 'activity_nr' in chunk_df.columns else None
        insert_df['standard'] = chunk_df['standard'].astype(str).str[:50] if 'standard' in chunk_df.columns else None
        insert_df['viol_type'] = chunk_df['viol_type'].astype(str).str[:50] if 'viol_type' in chunk_df.columns else None
        insert_df['description'] = chunk_df['description'].astype(str).str[:10000] if 'description' in chunk_df.columns else None
        
        # Penalty fields
        insert_df['initial_penalty'] = pd.to_numeric(chunk_df['initial_penalty'], errors='coerce') if 'initial_penalty' in chunk_df.columns else None
        insert_df['current_penalty'] = pd.to_numeric(chunk_df['current_penalty'], errors='coerce') if 'current_penalty' in chunk_df.columns else None
        insert_df['fta_penalty'] = pd.to_numeric(chunk_df['fta_penalty'], errors='coerce') if 'fta_penalty' in chunk_df.columns else None
        
        # Location and industry
        insert_df['site_state'] = chunk_df['site_state'].astype(str).str[:2] if 'site_state' in chunk_df.columns else None
        insert_df['site_city'] = chunk_df['site_city'].astype(str).str[:100] if 'site_city' in chunk_df.columns else None
        insert_df['naics_code'] = chunk_df['naics_code'].astype(str).str[:10] if 'naics_code' in chunk_df.columns else None
        insert_df['sic_code'] = chunk_df['sic_code'].astype(str).str[:10] if 'sic_code' in chunk_df.columns else None
        
        # Dates
        insert_df['violation_date'] = pd.to_datetime(chunk_df['open_date'], errors='coerce') if 'open_date' in chunk_df.columns else None
        # Extract year from year column if available, otherwise derive from violation_date
        insert_df['year'] = pd.to_numeric(chunk_df['year'], errors='coerce').astype('Int64') if 'year' in chunk_df.columns else None
        if insert_df['year'].isna().all() and insert_df['violation_date'].notna().any():
            insert_df['year'] = insert_df['violation_date'].dt.year.astype('Int64')
        
        # Replace empty strings with None
        insert_df = insert_df.replace('', None)
        
        return insert_df
    
    def _process_and_insert_violations(self, violations_df: pd.DataFrame, agency: str):
        """Process and insert violations (non-streaming fallback)."""
        processed = self._process_violation_chunk(violations_df, agency)
        if not processed.empty:
            _bulk_insert_dataframe(self.db.engine, 'violations', processed, use_native=True)
            logger.info(f"Successfully loaded {len(processed)} {agency} violations")
    
    def load_accidents_to_db(self, nrows: Optional[int] = None, force_reload: bool = False,
                             use_streaming: bool = True, chunk_size: int = 50000):
        """Load accidents from CSV into database (optimized streaming version)."""
        # Check if data already exists
        existing_count = self.db.get_table_row_count("accidents")
        if existing_count > 0 and not force_reload:
            logger.info(f"Accidents table already has {existing_count} records. Use force_reload=True to reload.")
            return
        
        # Get CSV file path
        csv_path = DATA_DIR / "osha_accident.csv"
        if not csv_path.exists():
            logger.info("CSV file not found, attempting to download...")
            load_csv_accidents(nrows=1)
            if not csv_path.exists():
                logger.error(f"Accident CSV file not found at {csv_path}")
                return
        
        # Optimize SQLite for bulk loading
        _optimize_sqlite_for_bulk_load(self.db.engine)
        
        session = self.db.get_session()
        try:
            # Delete existing records if force_reload
            if force_reload and existing_count > 0:
                logger.info(f"Deleting {existing_count} existing accident records...")
                session.query(Accident).delete()
                session.commit()
            
            # Drop indexes for faster inserts (accidents use single-column indexes, handled by SQLAlchemy)
            # No composite indexes to drop for accidents
            
            if use_streaming:
                self._load_accidents_streaming(csv_path, nrows, chunk_size)
            else:
                # Fallback to original method
                logger.info("Loading accidents from CSV (non-streaming mode)...")
                df = load_csv_accidents(nrows=nrows)
                if not df.empty:
                    self._process_and_insert_accidents(df)
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error loading accidents: {e}")
            raise
        finally:
            session.close()
    
    def _load_accidents_streaming(self, csv_path: Path, nrows: Optional[int], chunk_size: int):
        """Load accidents using streaming chunks."""
        logger.info(f"Loading accidents from {csv_path.name} using streaming chunks...")
        
        # Get total row count for progress tracking
        total_rows = _count_csv_rows(csv_path)
        if nrows:
            total_rows = min(total_rows, nrows)
        logger.info(f"Total rows to load: {total_rows:,}")
        
        rows_loaded = 0
        start_time = time.time()
        
        # Stream CSV in chunks
        for chunk_num, chunk_df in enumerate(
            pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False, nrows=nrows)
        ):
            # Process and insert chunk
            processed = self._process_accident_chunk(chunk_df)
            if not processed.empty:
                # Use native bulk import (executemany for SQLite, COPY for PostgreSQL)
                _bulk_insert_dataframe(self.db.engine, 'accidents', processed, use_native=True)
            
            rows_loaded += len(processed)
            
            # Progress logging
            elapsed = time.time() - start_time
            if elapsed > 0:
                rate = rows_loaded / elapsed
                remaining = (total_rows - rows_loaded) / rate if rate > 0 else 0
                pct = (rows_loaded / total_rows * 100) if total_rows > 0 else 0
                logger.info(
                    f"Chunk {chunk_num + 1}: {rows_loaded:,}/{total_rows:,} rows "
                    f"({pct:.1f}%) | Rate: {rate:.0f} rows/sec | ETA: {remaining/60:.1f} min"
                )
        
        total_time = time.time() - start_time
        logger.info(f"Successfully loaded {rows_loaded:,} accidents in {total_time/60:.1f} minutes")
    
    def _process_accident_chunk(self, chunk_df: pd.DataFrame) -> pd.DataFrame:
        """Process a chunk of accident data.
        
        Handles multiple formats:
        - OSHA standard format (accident_key, activity_nr, etc.)
        - OSHA fatality report format (summary_nr, event_date, etc.)
        - MSHA format (mine safety data)
        """
        insert_df = pd.DataFrame()
        
        # Detect format type
        is_msha_format = 'mine_id' in chunk_df.columns and 'ai_dt' in chunk_df.columns
        is_osha_fatality_format = 'summary_nr' in chunk_df.columns and 'event_date' in chunk_df.columns
        
        if is_msha_format:
            # MSHA format mapping
            # Create unique accident_key from mine_id and document_no
            if 'mine_id' in chunk_df.columns and 'document_no' in chunk_df.columns:
                insert_df['accident_key'] = (chunk_df['mine_id'].astype(str) + '_' + 
                                            chunk_df['document_no'].astype(str)).str[:50]
            elif 'mine_id' in chunk_df.columns:
                insert_df['accident_key'] = chunk_df['mine_id'].astype(str).str[:50]
            else:
                insert_df['accident_key'] = None
            
            insert_df['activity_nr'] = None  # MSHA doesn't link to OSHA inspections
            insert_df['estab_name'] = chunk_df['operator_name'].astype(str).str[:500] if 'operator_name' in chunk_df.columns else None
            # FIPS state code - using first 2 digits (may need proper mapping to state abbreviations)
            insert_df['site_state'] = chunk_df['fips_state_cd'].astype(str).str[:2] if 'fips_state_cd' in chunk_df.columns else None
            insert_df['naics_code'] = None  # MSHA doesn't have NAICS codes
            insert_df['accident_date'] = pd.to_datetime(chunk_df['ai_dt'], errors='coerce') if 'ai_dt' in chunk_df.columns else None
            # Extract year from ai_year, cal_yr, or accident_date (in order of preference)
            insert_df['year'] = pd.to_numeric(chunk_df['ai_year'], errors='coerce').astype('Int64') if 'ai_year' in chunk_df.columns else None
            if insert_df['year'].isna().all() and 'cal_yr' in chunk_df.columns:
                insert_df['year'] = pd.to_numeric(chunk_df['cal_yr'], errors='coerce').astype('Int64')
            if insert_df['year'].isna().all() and insert_df['accident_date'].notna().any():
                insert_df['year'] = insert_df['accident_date'].dt.year
            insert_df['description'] = chunk_df['ai_narr'].astype(str).str[:10000] if 'ai_narr' in chunk_df.columns else None
            # Determine fatality from injury degree description or code
            if 'inj_degr_desc' in chunk_df.columns:
                insert_df['fatality'] = chunk_df['inj_degr_desc'].astype(str).str.contains('FATAL', case=False, na=False)
            elif 'degree_injury_cd' in chunk_df.columns:
                # Code 1 typically indicates fatality in MSHA data
                insert_df['fatality'] = (chunk_df['degree_injury_cd'] == 1) if chunk_df['degree_injury_cd'].notna().any() else False
            else:
                insert_df['fatality'] = False
            # Use nature_injury if available, otherwise fall back to inj_degr_desc
            if 'nature_injury' in chunk_df.columns:
                insert_df['injury_type'] = chunk_df['nature_injury'].astype(str).str[:100]
            elif 'inj_degr_desc' in chunk_df.columns:
                insert_df['injury_type'] = chunk_df['inj_degr_desc'].astype(str).str[:100]
            else:
                insert_df['injury_type'] = None
        elif is_osha_fatality_format:
            # OSHA fatality report format (summary_nr, event_date, event_desc, etc.)
            insert_df['accident_key'] = chunk_df['summary_nr'].astype(str).str[:50] if 'summary_nr' in chunk_df.columns else None
            insert_df['activity_nr'] = None  # Fatality reports don't link to inspections
            insert_df['estab_name'] = None  # Not available in this format
            insert_df['site_state'] = chunk_df['state_flag'].astype(str).str[:2] if 'state_flag' in chunk_df.columns else None
            insert_df['naics_code'] = None  # Not available in this format
            insert_df['accident_date'] = pd.to_datetime(chunk_df['event_date'], errors='coerce') if 'event_date' in chunk_df.columns else None
            insert_df['year'] = None
            if insert_df['accident_date'].notna().any():
                insert_df['year'] = insert_df['accident_date'].dt.year
            # Combine event_desc and abstract_text for description
            if 'event_desc' in chunk_df.columns and 'abstract_text' in chunk_df.columns:
                # Combine both columns, handling NaN values
                event_desc = chunk_df['event_desc'].astype(str).replace('nan', '')
                abstract_text = chunk_df['abstract_text'].astype(str).replace('nan', '')
                combined = event_desc + ' | ' + abstract_text
                # Remove trailing separator if abstract_text is empty
                combined = combined.str.replace(' | $', '', regex=True)
                insert_df['description'] = combined.str[:10000]
            elif 'event_desc' in chunk_df.columns:
                insert_df['description'] = chunk_df['event_desc'].astype(str).str[:10000]
            elif 'abstract_text' in chunk_df.columns:
                insert_df['description'] = chunk_df['abstract_text'].astype(str).str[:10000]
            else:
                insert_df['description'] = None
            # Fatality field - 'X' indicates fatality
            if 'fatality' in chunk_df.columns:
                insert_df['fatality'] = (chunk_df['fatality'].astype(str).str.upper() == 'X')
            else:
                insert_df['fatality'] = False
            insert_df['injury_type'] = chunk_df['event_keyword'].astype(str).str[:100] if 'event_keyword' in chunk_df.columns else None
        else:
            # OSHA standard format (original expected format)
            insert_df['accident_key'] = chunk_df['accident_key'].astype(str).str[:50] if 'accident_key' in chunk_df.columns else None
            insert_df['activity_nr'] = chunk_df['activity_nr'].astype(str).str[:50] if 'activity_nr' in chunk_df.columns else None
            insert_df['estab_name'] = chunk_df['estab_name'].astype(str).str[:500] if 'estab_name' in chunk_df.columns else None
            insert_df['site_state'] = chunk_df['site_state'].astype(str).str[:2] if 'site_state' in chunk_df.columns else None
            insert_df['naics_code'] = chunk_df['naics_code'].astype(str).str[:10] if 'naics_code' in chunk_df.columns else None
            insert_df['accident_date'] = pd.to_datetime(chunk_df['accident_date'], errors='coerce') if 'accident_date' in chunk_df.columns else None
            # Extract year from year column or derive from accident_date
            insert_df['year'] = pd.to_numeric(chunk_df['year'], errors='coerce').astype('Int64') if 'year' in chunk_df.columns else None
            if insert_df['year'].isna().all() and insert_df['accident_date'].notna().any():
                insert_df['year'] = insert_df['accident_date'].dt.year
            insert_df['description'] = chunk_df['description'].astype(str).str[:10000] if 'description' in chunk_df.columns else None
            insert_df['fatality'] = pd.to_numeric(chunk_df['fatality'], errors='coerce').astype('boolean') if 'fatality' in chunk_df.columns else None
            insert_df['injury_type'] = chunk_df['injury_type'].astype(str).str[:100] if 'injury_type' in chunk_df.columns else None
        
        # Filter out rows with missing accident_key (required field)
        if 'accident_key' in insert_df.columns:
            insert_df = insert_df[insert_df['accident_key'].notna()]
        
        # Replace empty strings with None
        insert_df = insert_df.replace('', None)
        
        return insert_df
    
    def _process_and_insert_accidents(self, df: pd.DataFrame):
        """Process and insert accidents (non-streaming fallback)."""
        processed = self._process_accident_chunk(df)
        if not processed.empty:
            _bulk_insert_dataframe(self.db.engine, 'accidents', processed, use_native=True)
            logger.info(f"Successfully loaded {len(processed)} accidents")
    
    def load_all_data(self, nrows: Optional[int] = None, force_reload: bool = False,
                     use_parallel: bool = True, num_workers: Optional[int] = None,
                     tables: Optional[list] = None):
        """
        Load data types into database.
        
        Args:
            nrows: Limit number of rows to load (None = all)
            force_reload: If True, delete existing records and reload
            use_parallel: If True, use parallel processing for large datasets (default: True)
            num_workers: Number of parallel workers (default: auto-detect)
            tables: List of tables to load. Options: ['inspections', 'violations', 'accidents'].
                    If None, loads all tables.
        """
        import multiprocessing as mp
        
        # Default to all tables if not specified
        if tables is None:
            tables = ['inspections', 'violations', 'accidents']
        
        # Validate table names
        valid_tables = ['inspections', 'violations', 'accidents']
        invalid_tables = [t for t in tables if t not in valid_tables]
        if invalid_tables:
            raise ValueError(f"Invalid table names: {invalid_tables}. Valid options: {valid_tables}")
        
        logger.info(f"Loading data into database (tables: {', '.join(tables)})...")
        
        # Check database type - SQLite has single-writer limitation
        database_url = str(self.db.engine.url)
        is_sqlite = "sqlite" in database_url
        
        # Auto-detect workers if not specified
        if num_workers is None and use_parallel:
            if is_sqlite:
                # SQLite: Limit to 2-4 workers due to single-writer limitation
                num_workers = min(mp.cpu_count(), 4)
                logger.info(f"SQLite detected: Using {num_workers} workers (limited due to single-writer)")
            else:
                # PostgreSQL: Can use more workers
                num_workers = min(mp.cpu_count(), 8)
                logger.info(f"Auto-detected {num_workers} workers for parallel processing")
        
        # For SQLite, cap workers at 4 to avoid database lock issues
        if is_sqlite and use_parallel and num_workers > 4:
            logger.warning("SQLite detected: Reducing workers to 4 to avoid database lock issues")
            num_workers = 4
        
        # Load inspections (can use parallel)
        if 'inspections' in tables:
            self.load_inspections_to_db(
                nrows=nrows, 
                force_reload=force_reload,
                use_streaming=True,
                use_parallel=use_parallel,
                num_workers=num_workers
            )
        
        # Load violations (streaming only for now, parallel can be added later)
        if 'violations' in tables:
            self.load_violations_to_db(
                nrows=nrows, 
                force_reload=force_reload, 
                agency="OSHA",
                use_streaming=True
            )
        
        # Load accidents (streaming only for now)
        if 'accidents' in tables:
            self.load_accidents_to_db(
                nrows=nrows, 
                force_reload=force_reload,
                use_streaming=True
            )
        
        logger.info("Data loading complete!")
    
    # ========================================================================
    # QUERY METHODS - PUBLIC API
    # ========================================================================
    
    def query_inspections(self, limit: Optional[int] = None, **filters) -> pd.DataFrame:
        """Query inspections from database."""
        session = self.db.get_session()
        try:
            query = session.query(Inspection)
            
            # Apply filters
            if "year" in filters and filters["year"]:
                query = query.filter(Inspection.year == filters["year"])
            if "state" in filters and filters["state"]:
                query = query.filter(Inspection.site_state == filters["state"].upper())
            if "naics_code" in filters and filters["naics_code"]:
                query = query.filter(Inspection.naics_code.like(f"{filters['naics_code']}%"))
            
            if limit:
                query = query.limit(limit)
            
            df = pd.read_sql(query.statement, session.bind)
            return df
        finally:
            session.close()
    
    def query_violations(self, limit: Optional[int] = None, **filters) -> pd.DataFrame:
        """Query violations from database."""
        session = self.db.get_session()
        try:
            query = session.query(Violation)
            
            # Apply filters
            if "agency" in filters and filters["agency"]:
                query = query.filter(Violation.agency == filters["agency"])
            if "company_name" in filters and filters["company_name"]:
                from .fuzzy_matcher import CompanyNameMatcher
                from sqlalchemy import func
                normalized = CompanyNameMatcher().normalize_company_name(filters["company_name"])
                company_name_lower = filters["company_name"].lower()
                query = query.filter(
                    (Violation.company_name_normalized.contains(normalized)) |
                    (func.lower(Violation.company_name).like(f"%{company_name_lower}%"))
                )
            if "year" in filters and filters["year"]:
                query = query.filter(Violation.year == filters["year"])
            if "state" in filters and filters["state"]:
                query = query.filter(Violation.site_state == filters["state"].upper())
            if "min_penalty" in filters and filters["min_penalty"]:
                query = query.filter(Violation.current_penalty >= filters["min_penalty"])
            
            if limit:
                query = query.limit(limit)
            
            df = pd.read_sql(query.statement, session.bind)
            return df
        finally:
            session.close()

