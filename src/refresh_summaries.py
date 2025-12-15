"""
Script to refresh pre-aggregated summary tables.
Can be run as a scheduled job or after data updates.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db_manager
from src.summary_tables import SummaryTableManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for refreshing summary tables."""
    parser = argparse.ArgumentParser(description="Refresh pre-aggregated summary tables")
    parser.add_argument(
        "--database-url",
        type=str,
        help="Database URL (default: uses data_dir)"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Data directory (default: ./data)"
    )
    parser.add_argument(
        "--agency",
        type=str,
        help="Refresh summaries for specific agency only (e.g., OSHA)"
    )
    parser.add_argument(
        "--create-tables",
        action="store_true",
        help="Create summary tables if they don't exist"
    )
    
    args = parser.parse_args()
    
    # Initialize database manager
    db_manager = get_db_manager(
        database_url=args.database_url,
        data_dir=Path(args.data_dir) if args.data_dir else None
    )
    
    # Initialize summary manager
    summary_manager = SummaryTableManager(db_manager)
    
    # Create tables if requested
    if args.create_tables:
        logger.info("Creating summary tables...")
        summary_manager.create_tables()
    
    # Refresh summaries
    try:
        logger.info(f"Refreshing summary tables{' for agency: ' + args.agency if args.agency else ''}...")
        summary_manager.refresh_all_summaries(agency=args.agency)
        logger.info("Summary tables refreshed successfully!")
    except Exception as e:
        logger.error(f"Error refreshing summary tables: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

