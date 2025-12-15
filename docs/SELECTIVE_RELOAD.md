# Selective Reload Feature

## Overview

The selective reload feature allows you to reload specific database tables without reloading all data. This is especially useful when:
- Only one table's data has changed
- You need to fix data issues in a specific table
- You want faster updates for incremental data changes

## Usage

### Command-Line Interface

```bash
# Reload only accidents table
python -m src.db_migration --force-reload --tables accidents

# Reload multiple tables
python -m src.db_migration --force-reload --tables inspections violations

# Reload all tables (default behavior)
python -m src.db_migration --force-reload
```

### Available Tables

- `inspections` - OSHA inspection records
- `violations` - OSHA violation citations
- `accidents` - OSHA accident/fatality reports

### Examples

**Reload only accidents after downloading new accident data:**
```bash
# Download new accident CSV
python src/data_loader.py

# Reload only accidents table
python -m src.db_migration --force-reload --tables accidents
```

**Reload inspections and violations together:**
```bash
python -m src.db_migration --force-reload --tables inspections violations
```

**Reload with parallel processing:**
```bash
python -m src.db_migration --force-reload --tables violations --workers 4
```

## Programmatic Usage

```python
from src.db_loader import DatabaseDataLoader

loader = DatabaseDataLoader()

# Reload specific tables
loader.load_all_data(
    force_reload=True,
    tables=['accidents']  # Only reload accidents
)

# Reload multiple tables
loader.load_all_data(
    force_reload=True,
    tables=['inspections', 'violations']
)

# Reload all tables (default)
loader.load_all_data(force_reload=True)
```

## Benefits

| Scenario | Without Selective Reload | With Selective Reload |
|----------|------------------------|----------------------|
| Update accidents only | Reload all 3 tables (~15 min) | Reload accidents only (~2 min) |
| Fix violations data | Reload all 3 tables (~15 min) | Reload violations only (~8 min) |
| Incremental updates | Full reload every time | Update only changed tables |

## How It Works

1. **Table Validation**: The system validates that specified table names are valid
2. **Selective Loading**: Only the specified tables are processed
3. **Index Management**: Indexes are dropped and recreated only for affected tables
4. **Parallel Processing**: Parallel processing (if enabled) applies to inspections table only

## Notes

- **Inspections**: Supports parallel processing when enabled
- **Violations**: Uses streaming chunked loading (parallel support coming soon)
- **Accidents**: Uses streaming chunked loading with multi-format support

## Multi-Format Support

The accidents table supports automatic format detection for:
- **OSHA Standard Format** - Standard accident CSV format
- **OSHA Fatality Reports** - Fatality report format (summary_nr, event_date, etc.)
- **MSHA Format** - Mine Safety and Health Administration format

The loader automatically detects and maps columns from these formats to the standard accident schema.

## Troubleshooting

### "Invalid table names" error
Make sure you're using valid table names: `inspections`, `violations`, or `accidents`

```bash
# Correct
python -m src.db_migration --force-reload --tables accidents

# Incorrect
python -m src.db_migration --force-reload --tables accident  # Missing 's'
```

### Tables not reloading
Ensure you're using `--force-reload` flag:

```bash
# This will skip if data exists
python -m src.db_migration --tables accidents

# This will force reload
python -m src.db_migration --force-reload --tables accidents
```

## Performance Tips

1. **Use selective reload** when only one table changes
2. **Combine with parallel processing** for inspections:
   ```bash
   python -m src.db_migration --force-reload --tables inspections --workers 4
   ```
3. **Monitor progress** - The loader shows real-time progress for each table

## Related Documentation

- [Database Setup Guide](DATABASE_SETUP.md) - General database setup
- [Using Parallel Processing](USING_PARALLEL_PROCESSING.md) - Parallel processing details
- [Streaming Loader Implementation](STREAMING_LOADER_IMPLEMENTATION.md) - Streaming architecture

