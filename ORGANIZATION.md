# Codebase Organization

This document describes the organization and structure of the codebase.

## Directory Structure

```
OSHA-Violation-Analyzer/
│
├── Root Level Files
│   ├── app.py                  # Main Streamlit application
│   ├── requirements.txt        # Python dependencies
│   ├── pytest.ini              # Test configuration
│   ├── Dockerfile              # Docker container definition
│   ├── docker-compose.yml      # Multi-service Docker setup
│   ├── .env.example            # Environment variables template (development)
│   ├── .env.production.example # Environment variables template (production)
│   ├── .gitignore              # Git ignore rules
│   ├── LICENSE                 # License file
│   ├── CHANGELOG.md            # Change history
│   ├── ORGANIZATION.md         # Codebase organization guide
│   └── README.md               # Main documentation (start here!)
│
├── api/                        # REST API Application
│   ├── __init__.py
│   └── main.py                 # FastAPI application with all endpoints
│
├── src/                        # Source Code
│   ├── Core Analysis
│   │   ├── analyzer.py         # CSV-based OSHA analyzer (legacy)
│   │   ├── analyzer_db.py      # Database-backed analyzer (recommended)
│   │   └── compliance_analyzer.py # Multi-agency compliance analysis
│   │
│   ├── Database
│   │   ├── database.py         # SQLAlchemy models and database manager
│   │   ├── db_loader.py        # Database data loading utilities
│   │   ├── db_migration.py     # CSV to database migration tool
│   │   └── summary_tables.py   # Pre-aggregated summary tables
│   │
│   ├── Data Management
│   │   ├── data_loader.py      # OSHA CSV data loading
│   │   ├── agency_base.py      # Base class for agency data loaders
│   │   └── epa_loader.py       # EPA/MSHA/FDA loader framework
│   │
│   ├── Analysis Features
│   │   ├── fuzzy_matcher.py    # Company name fuzzy matching
│   │   ├── risk_scorer.py      # Risk scoring system
│   │   ├── violation_impact.py # Violation impact analysis
│   │   └── violation_impact_viz.py # Impact visualizations
│   │
│   ├── Infrastructure
│   │   ├── cache.py            # Caching layer
│   │   ├── config.py           # Configuration management
│   │   ├── monitoring.py       # Monitoring and logging
│   │   ├── data_validation.py  # Data validation framework
│   │   ├── download_agent.py   # AI-powered download agent
│   │   └── refresh_summaries.py # Summary table refresh utility
│   │
│   └── __init__.py
│
├── tests/                      # Test Suite
│   ├── __init__.py
│   ├── test_analyzer_db.py     # Database analyzer tests
│   ├── test_fuzzy_matcher.py   # Fuzzy matching tests
│   └── test_data_validation.py # Validation tests
│
├── scripts/                    # Utility Scripts
│   ├── Data Management
│   │   ├── check_data_status.py      # Check data file status
│   │   ├── find_and_setup_data.py    # Find and organize downloaded files
│   │   └── combine_and_setup_data.py # Combine fragmented CSVs
│   │
│   ├── Downloads
│   │   ├── download_with_ai.py       # AI-powered download script
│   │   ├── download_data_helper.py   # Download helper utilities
│   │   └── run_ai_download.sh        # Shell script wrapper
│   │
│   ├── Examples & Testing
│   │   ├── test_amazon.py            # Amazon test example
│   │   ├── test_average_fine_2007.py # Average fine test
│   │   └── example_db_usage.py       # Database usage examples
│   │
│   ├── Database Utilities
│   │   ├── update_year_batched.py    # Batch year updates
│   │   ├── update_year_bulk.py       # Bulk year updates
│   │   └── update_year_ultra_fast.py # Fast year updates
│   │
│   ├── Configuration
│   │   └── validate_env.py           # Environment variable validation
│   │
│   └── README.md                     # Scripts documentation
│
├── docs/                       # Documentation
│   ├── DOCUMENTATION.md        # Documentation index (start here)
│   ├── Quick Start
│   │   ├── DATABASE_SETUP.md
│   │   ├── DATA_DOWNLOAD_GUIDE.md
│   │   ├── QUICK_LOAD_TIP.md
│   │   └── QUICK_START_AI_DOWNLOAD.md
│   ├── Features
│   │   ├── FUZZY_MATCHING_AND_RISK_SCORING.md
│   │   ├── VIOLATION_IMPACT_ANALYSIS.md
│   │   └── RUN_AMAZON_TEST.md
│   ├── Architecture
│   │   ├── ARCHITECTURE_IMPROVEMENTS.md
│   │   ├── DATABASE_ARCHITECTURE_IMPROVEMENTS.md
│   │   ├── IMPLEMENTATION_SUMMARY.md
│   │   ├── ADDITIONAL_IMPROVEMENTS.md
│   │   ├── STATUS_SUMMARY.md
│   │   └── ENHANCEMENTS.md
│   ├── Configuration
│   │   └── ENVIRONMENT_VARIABLES.md  # Environment variable reference
│   └── Guides
│       ├── AI_DOWNLOAD_GUIDE.md
│       ├── QUICK_START_AI_DOWNLOAD.md
│       └── MANUAL_DOWNLOAD_STEPS.md
│
└── data/                       # Data Files (gitignored)
    ├── osha_inspection.csv
    ├── osha_violation.csv
    ├── osha_accident.csv
    └── compliance.db           # SQLite database (created after migration)
```

## File Organization Principles

### Root Directory
Contains only essential files needed to run and configure the application:
- Main application entry point (`app.py`)
- Configuration files (`requirements.txt`, `pytest.ini`, `.env.example`)
- Docker files
- License and main README

### `src/` Directory
Contains all source code organized by functionality:
- **Core Analysis**: Main analyzer classes
- **Database**: Database models, loaders, and migration tools
- **Data Management**: Data loading and preprocessing
- **Analysis Features**: Feature implementations (fuzzy matching, risk scoring, etc.)
- **Infrastructure**: Supporting infrastructure (cache, config, monitoring, validation)

### `api/` Directory
REST API application (FastAPI):
- Self-contained API application
- All API endpoints in `main.py`

### `tests/` Directory
Test suite following pytest conventions:
- Unit tests for each major component
- Test files mirror source structure

### `scripts/` Directory
Utility scripts for various tasks:
- **Data Management**: Scripts for managing data files
- **Downloads**: Scripts for downloading data
- **Examples**: Example scripts and test cases

### `docs/` Directory
All documentation files organized by category:
- **Quick Start**: Getting started guides
- **Features**: Feature-specific documentation
- **Architecture**: Architecture and improvement documentation
- **Guides**: How-to guides

### `data/` Directory
Data files (gitignored):
- CSV files
- Database files
- Other data artifacts

## Naming Conventions

- **Python modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Documentation**: `UPPER_SNAKE_CASE.md` for easy identification

## Adding New Files

When adding new files:

1. **Source code** → Place in `src/` in appropriate subcategory
2. **Tests** → Place in `tests/` mirroring source structure
3. **Utility scripts** → Place in `scripts/` with appropriate category
4. **Documentation** → Place in `docs/` with appropriate category
5. **API code** → Place in `api/`

## Import Organization

All Python files should follow this import order:

1. **Standard library imports** (alphabetically sorted)
2. **Third-party imports** (alphabetically sorted)
3. **Local imports** (alphabetically sorted)
4. **Blank line** between each group

Example:
```python
# Standard library imports
import logging
from pathlib import Path
from typing import Dict, Optional

# Third-party imports
import pandas as pd
from sqlalchemy import func

# Local imports
from .cache import cached
from .database import get_db_manager, Violation
```

## Import Paths

When importing from `src/`:
```python
from src.module_name import ClassName
```

When importing in scripts from `scripts/`:
```python
# Adjust path if needed
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.module_name import ClassName
```

## Recent Additions

### Environment Configuration
- `.env.example` - Development environment variables template
- `.env.production.example` - Production environment variables template
- `scripts/validate_env.py` - Environment variable validation script
- `docs/ENVIRONMENT_VARIABLES.md` - Complete environment variable documentation

### Code Organization Improvements
- Standardized import organization across all files
- Consistent logging instead of print statements
- Removed unused imports
- Improved code documentation

