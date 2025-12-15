"""
Database Migration Utility
Helper script to migrate CSV data to database and manage database operations.
"""

import argparse
import logging
from pathlib import Path
from .database import get_db_manager, reset_db_manager
from .db_loader import DatabaseDataLoader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def migrate_csv_to_db(data_dir: Path, force_reload: bool = False, nrows: int = None,
                     use_parallel: bool = True, num_workers: int = None, tables: list = None):
    """
    Migrate CSV data to database.
    
    Args:
        data_dir: Directory containing CSV files
        force_reload: If True, delete existing records and reload
        nrows: Limit number of rows to load (for testing)
        use_parallel: If True, use parallel processing (default: True)
        num_workers: Number of parallel workers (default: auto-detect)
        tables: List of tables to load. Options: ['inspections', 'violations', 'accidents'].
                If None, loads all tables.
    """
    logger.info("Starting CSV to database migration...")
    
    db_loader = DatabaseDataLoader(data_dir=data_dir)
    
    try:
        db_loader.load_all_data(
            nrows=nrows, 
            force_reload=force_reload,
            use_parallel=use_parallel,
            num_workers=num_workers,
            tables=tables
        )
        logger.info("Migration completed successfully!")
        
        # Print statistics
        stats = db_loader.db.get_stats()
        logger.info("\nDatabase Statistics:")
        logger.info(f"  Database: {stats['database_url']}")
        for table, info in stats['tables'].items():
            if info.get('exists'):
                logger.info(f"  {table}: {info.get('row_count', 0):,} rows")
            else:
                logger.info(f"  {table}: not found")
    
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


def main():
    """Command-line interface for database operations."""
    parser = argparse.ArgumentParser(description='Database migration and management utility')
    parser.add_argument(
        '--data-dir',
        type=Path,
        default=Path(__file__).parent.parent / "data",
        help='Directory containing CSV data files (default: ./data)'
    )
    parser.add_argument(
        '--force-reload',
        action='store_true',
        help='Force reload of specified tables (deletes existing records). Use with --tables to reload specific tables only.'
    )
    parser.add_argument(
        '--nrows',
        type=int,
        default=None,
        help='Limit number of rows to load (for testing)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics and exit'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset database (drop all tables)'
    )
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Disable parallel processing (use single-threaded)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of parallel workers (default: auto-detect, max 8)'
    )
    parser.add_argument(
        '--tables',
        type=str,
        nargs='+',
        choices=['inspections', 'violations', 'accidents'],
        default=None,
        help='Selective reload: specify which tables to load (e.g., --tables accidents). '
             'If not specified, all tables are loaded.'
    )
    
    args = parser.parse_args()
    
    if args.reset:
        logger.warning("Resetting database (dropping all tables)...")
        db = get_db_manager(data_dir=args.data_dir)
        db.drop_tables()
        db.create_tables()
        logger.info("Database reset complete!")
        return
    
    if args.stats:
        db = get_db_manager(data_dir=args.data_dir)
        stats = db.get_stats()
        print("\nDatabase Statistics:")
        print(f"  Database: {stats['database_url']}")
        for table, info in stats['tables'].items():
            if info.get('exists'):
                print(f"  {table}: {info.get('row_count', 0):,} rows")
            else:
                print(f"  {table}: not found")
        return
    
    # Perform migration
    migrate_csv_to_db(
        data_dir=args.data_dir,
        force_reload=args.force_reload,
        nrows=args.nrows,
        use_parallel=not args.no_parallel,
        num_workers=args.workers,
        tables=args.tables
    )


if __name__ == "__main__":
    main()

