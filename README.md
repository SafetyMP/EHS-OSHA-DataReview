# Multi-Agency Compliance Analyzer

An interactive tool for analyzing compliance and enforcement data across multiple regulatory agencies (OSHA, EPA, MSHA, FDA) to identify enforcement trends, high-risk industries, and cross-agency compliance patterns.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)

## Overview

This tool transforms raw enforcement data from multiple regulatory agencies into actionable insights for:
- **Safety Professionals** — Benchmark your industry's violation rates and identify common citations across agencies
- **Compliance Teams** — Understand penalty trends and enforcement priorities by region and agency
- **Risk Analysts** — Cross-compare company compliance records across OSHA, EPA, MSHA, and FDA
- **Researchers** — Analyze patterns in environmental, health, and safety enforcement over time

## Features

### OSHA Analysis
- 🔍 **Search & Filter** — Query violations by industry (NAICS/SIC), state, date range, or keyword
- 📊 **Trend Analysis** — Visualize inspection volumes and penalty amounts over time
- 🏭 **Industry Benchmarking** — Compare violation rates across sectors
- 💰 **Penalty Intelligence** — Analyze fine distributions by violation type and severity
- 📍 **Geographic Insights** — Map enforcement activity by state and region

### Multi-Agency Company Comparison
- 🏢 **Cross-Agency Search** — Search for companies across OSHA, EPA, MSHA, and FDA databases
- 📊 **Compliance Comparison** — Compare a company's violation history across multiple agencies
- 🔗 **Fuzzy Matching** — Intelligent company name normalization for accurate cross-agency matching
- 📈 **Violation Summary** — Get comprehensive compliance summaries with penalties by agency
- 🎯 **Risk Scoring** — Composite risk assessment based on violation count, penalties, recency, and multi-agency presence
- 📉 **Violation Impact Analysis** — Analyze whether violations increased or reduced subsequent compliance

### API Access
- 🌐 **REST API** — Full RESTful API with OpenAPI documentation
- 📄 **Pagination** — Efficient handling of large result sets
- 🔍 **Advanced Filtering** — Comprehensive query parameters
- 📊 **Statistics Endpoints** — Database and cache statistics

## Data Sources

### OSHA Data
Data is sourced from the [U.S. Department of Labor Enforcement Data Catalog](https://enforcedata.dol.gov/views/data_catalogs.php), which includes:
- **Inspections** — ~100,000 OSHA inspections conducted annually since 1970
- **Violations** — Citation details with penalty assessments
- **Accidents** — Investigation narratives with injury/fatality details

### Multi-Agency Support
The framework supports additional agencies with data loader implementations:
- **EPA (Environmental Protection Agency)** — ECHO database for environmental violations (framework ready)
- **MSHA (Mine Safety and Health Administration)** — Mine safety and health violations (framework ready)
- **FDA (Food and Drug Administration)** — Food and drug safety violations (framework ready)

Note: EPA, MSHA, and FDA loaders are included but require data integration. The structure is ready for easy integration when data sources are available.

## Installation

```bash
# Clone the repository
git clone https://github.com/SafetyMP/EHS-OSHA-DataReview.git
cd OSHA-Violation-Analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Configure environment variables
cp .env.example .env
# Edit .env with your configuration

# Download OSHA data (first run only) - see docs/DATA_DOWNLOAD_GUIDE.md
python src/data_loader.py

# Or use helper script to find and organize downloaded files
python scripts/find_and_setup_data.py

# (Recommended) Migrate to database for better performance
python -m src.db_migration

# (Optional) Reload specific tables only (faster updates)
python -m src.db_migration --force-reload --tables accidents

# (Optional) Refresh pre-aggregated summary tables for faster queries
python -m src.refresh_summaries --create-tables

# Launch the dashboard
streamlit run app.py
```

### Alternative: Using Docker

```bash
# Build and run with Docker Compose
docker-compose up

# Or build and run individually
docker build -t osha-analyzer .
docker run -p 8501:8501 -v $(pwd)/data:/app/data osha-analyzer
```

### Using the REST API

```bash
# Start the API server
uvicorn api.main:app --reload --port 8000

# Access API documentation at:
# http://localhost:8000/docs
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

## Project Structure

```
OSHA-Violation-Analyzer/
├── app.py                      # Streamlit dashboard (main entry point)
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Multi-service Docker setup
├── Dockerfile                  # Container definition
├── pytest.ini                  # Test configuration
├── .env.example                # Environment variables template (development)
├── .env.production.example     # Environment variables template (production)
├── LICENSE                     # License file
│
├── api/                        # REST API
│   ├── __init__.py
│   └── main.py                 # FastAPI application
│
├── src/                        # Source code
│   ├── __init__.py
│   ├── data_loader.py          # OSHA data fetching and preprocessing
│   ├── analyzer.py             # OSHA-specific analysis (CSV-based, legacy)
│   ├── analyzer_db.py          # Database-backed analyzer (recommended)
│   ├── database.py             # Database models and setup (SQLAlchemy)
│   ├── db_loader.py            # Database data loader and queries
│   ├── db_migration.py         # Migration utility (CSV → Database)
│   ├── agency_base.py          # Base class for agency data loaders
│   ├── epa_loader.py           # EPA/MSHA/FDA data loaders (framework)
│   ├── compliance_analyzer.py  # Multi-agency compliance analysis
│   ├── fuzzy_matcher.py        # Company name fuzzy matching
│   ├── risk_scorer.py          # Risk scoring system
│   ├── violation_impact.py     # Violation impact analysis
│   ├── violation_impact_viz.py # Impact visualization
│   ├── cache.py                # Caching layer
│   ├── config.py               # Configuration management
│   ├── monitoring.py           # Monitoring and logging
│   ├── data_validation.py      # Data validation framework
│   ├── summary_tables.py       # Pre-aggregated summary tables
│   ├── refresh_summaries.py    # Summary table refresh utility
│   └── download_agent.py       # AI-powered download agent
│
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── test_analyzer_db.py     # Database analyzer tests
│   ├── test_fuzzy_matcher.py   # Fuzzy matching tests
│   └── test_data_validation.py # Validation tests
│
├── scripts/                    # Utility scripts
│   ├── check_data_status.py    # Check data file status
│   ├── combine_and_setup_data.py # Combine fragmented CSV files
│   ├── download_data_helper.py # Download helper utilities
│   ├── download_with_ai.py     # AI-powered download script
│   ├── find_and_setup_data.py  # Find and organize downloaded files
│   ├── test_amazon.py          # Amazon test example
│   ├── example_db_usage.py     # Database usage examples
│   └── run_ai_download.sh      # Shell script for AI downloads
│
├── docs/                       # Documentation
│   ├── DOCUMENTATION.md        # Documentation index
│   ├── DATABASE_SETUP.md       # Database setup guide
│   ├── ARCHITECTURE_IMPROVEMENTS.md # Architecture guide
│   ├── IMPLEMENTATION_SUMMARY.md    # Implementation summary
│   ├── STATUS_SUMMARY.md       # Current status
│   ├── ADDITIONAL_IMPROVEMENTS.md   # Additional improvements
│   ├── DATA_DOWNLOAD_GUIDE.md  # Data download instructions
│   ├── AI_DOWNLOAD_GUIDE.md    # AI download guide
│   ├── QUICK_LOAD_TIP.md       # Performance tips
│   ├── FUZZY_MATCHING_AND_RISK_SCORING.md # Feature docs
│   ├── VIOLATION_IMPACT_ANALYSIS.md # Feature docs
│   └── [other documentation files...]
│
└── data/                       # Downloaded datasets (gitignored)
    ├── osha_inspection.csv
    ├── osha_violation.csv
    ├── osha_accident.csv
    └── compliance.db           # SQLite database (created after migration)
```

## Usage Examples

### Search violations by industry (OSHA)

**Using CSV-based analyzer (original):**
```python
from src.analyzer import OSHAAnalyzer

analyzer = OSHAAnalyzer()
# Find top violations in manufacturing (NAICS 31-33)
results = analyzer.search_violations(naics_prefix="31", year=2023)
```

**Using database-backed analyzer (recommended for better performance):**
```python
from src.analyzer_db import OSHAAnalyzerDB

# Initialize database-backed analyzer (faster for large datasets)
analyzer = OSHAAnalyzerDB()

# Same API, but uses database queries
results = analyzer.search_violations(naics_prefix="31", year=2023)
top_violations = analyzer.top_violations(n=10)

# Check database statistics
stats = analyzer.get_stats()
print(f"Violations in database: {stats['tables']['violations']['row_count']:,}")
```

**Note:** The app automatically detects and uses the database backend if available. Run `python -m src.db_migration` first to load data into database for optimal performance. See [DATABASE_SETUP.md](DATABASE_SETUP.md) for details.

### Cross-agency company search (NEW!)
```python
from src.compliance_analyzer import ComplianceAnalyzer

# Initialize multi-agency analyzer
comp_analyzer = ComplianceAnalyzer()

# Search for a company across all agencies
company_violations = comp_analyzer.search_company("Acme Corporation")

# Get comprehensive compliance summary
summary = comp_analyzer.compare_company_across_agencies("Acme Corporation")
print(f"Total violations: {summary['total_violations']}")
print(f"Total penalties: ${summary['total_penalties']:,.2f}")
print(f"Agencies: {list(summary['agencies'].keys())}")

# Find companies with violations across multiple agencies
cross_agency_companies = comp_analyzer.get_companies_with_cross_agency_violations(
    min_violations=1
)
```

### Analyze penalty trends
```python
# Get average penalties by violation type (OSHA)
penalties = analyzer.penalty_summary(group_by="violation_type")
```

## Sample Insights

| Metric | Value |
|--------|-------|
| Most cited standard | 1910.134 - Respiratory Protection |
| Highest avg. penalty industry | Construction (NAICS 23) |
| States with most inspections | CA, TX, FL, NY, IL |

## Recent Enhancements ✨

### Database Backend & Performance
- ✅ **Database-first architecture** - Instant startup (vs 5-15 min load time)
- ✅ **Connection pooling** - Efficient resource management
- ✅ **Query optimization** - Enhanced indexes for 10-100x faster queries
- ✅ **Pre-aggregated summaries** - Fast lookups for common aggregations
- ✅ **Pagination** - Efficient handling of large result sets
- ✅ **Selective reload** - Reload specific tables without full database reload
- ✅ **Parallel processing** - Multi-core support for faster data loading
- ✅ **Streaming chunked loading** - Memory-efficient processing of large datasets
- ✅ **Multi-format support** - Automatic detection and mapping of different CSV formats

### Advanced Features
- ✅ **Fuzzy company matching** - Intelligent name normalization across agencies
- ✅ **Risk scoring system** - Composite risk assessment based on multiple factors
- ✅ **Violation impact analysis** - Before/after analysis of compliance patterns
- ✅ **Multi-agency comparison** - Cross-agency compliance tracking

### API & Infrastructure
- ✅ **REST API** - Full FastAPI implementation with OpenAPI docs
- ✅ **Docker support** - Containerized deployment
- ✅ **Configuration management** - Environment-based settings with `.env` templates
- ✅ **Environment validation** - Pre-deployment validation script for configuration
- ✅ **Monitoring & logging** - Performance tracking and observability
- ✅ **Data validation** - Quality checks and validation framework
- ✅ **Test suite** - Comprehensive pytest tests

### Data Analysis Improvements
- ✅ **Unknown sector classification** - Intelligent classification of violations with missing NAICS codes
- ✅ **Enhanced industry analysis** - Automatic sector assignment based on company name patterns
- ✅ **Improved data display** - Full precision penalty amounts in overview metrics

## Roadmap

- [x] Multi-agency framework for cross-agency company comparisons
- [x] Company name normalization for accurate entity matching
- [x] Database backend for improved performance
- [x] REST API for programmatic access
- [x] Fuzzy matching and risk scoring
- [x] Violation impact analysis
- [ ] Integrate EPA ECHO API data
- [ ] Integrate MSHA enforcement data
- [ ] Integrate FDA enforcement data
- [ ] Add NLP analysis of accident narratives
- [ ] Predictive risk scoring by establishment (framework ready)

## Configuration

### Environment Variables

The application uses environment variables for configuration. See [docs/ENVIRONMENT_VARIABLES.md](docs/ENVIRONMENT_VARIABLES.md) for complete documentation.

**Quick Setup:**
```bash
# Development
cp .env.example .env
# Edit .env with your values

# Production
cp .env.production.example .env.production
# Edit .env.production with production values

# Validate configuration
python scripts/validate_env.py --load-env .env
```

**Key Configuration Options:**
- `DATABASE_URL` - Database connection string (defaults to SQLite)
- `DATA_DIR` - Path to data directory
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `OPENAI_API_KEY` - Required for AI-powered download features
- `SECRET_KEY` - Required for production (session management)

## Documentation

For detailed documentation, see:
- **[docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)** - Complete documentation index
- **[docs/ENVIRONMENT_VARIABLES.md](docs/ENVIRONMENT_VARIABLES.md)** - Environment variable reference
- **[docs/DATABASE_SETUP.md](docs/DATABASE_SETUP.md)** - Database setup guide
- **[docs/ARCHITECTURE_IMPROVEMENTS.md](docs/ARCHITECTURE_IMPROVEMENTS.md)** - Architecture guide
- **[docs/STATUS_SUMMARY.md](docs/STATUS_SUMMARY.md)** - Implementation status

All documentation is located in the `docs/` directory.

## Performance

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| App Startup | 5-15 min | Instant | **100x+ faster** |
| Query Performance | Full table scan | Indexed | **10-100x faster** |
| Aggregation Queries | Real-time | Pre-computed | **100x+ faster** |
| Memory Usage | All data in RAM | Query results only | **90%+ reduction** |

## Technology Stack

- **Backend**: Python 3.9+, SQLAlchemy, FastAPI
- **Database**: SQLite (dev) / PostgreSQL (production-ready)
- **Frontend**: Streamlit
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly
- **Testing**: Pytest
- **Containerization**: Docker, Docker Compose

## Contributing

Contributions welcome! Please open an issue or submit a PR.

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

Copyright 2025 Sage Hart

## Author

**Sage Hart** — [LinkedIn](https://linkedin.com/in/shporter) | [GitHub](https://github.com/SafetyMP)

*Built to help organizations proactively identify and address workplace safety risks.*
