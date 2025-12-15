# Scripts Directory

This directory contains utility scripts for data management, testing, and setup.

## Data Management Scripts

### `check_data_status.py`
Check the status of data files in the `data/` directory.

```bash
python scripts/check_data_status.py
```

### `find_and_setup_data.py`
Find downloaded OSHA data files and set them up correctly.

```bash
python scripts/find_and_setup_data.py
```

### `combine_and_setup_data.py`
Combine fragmented CSV files into single, usable files.

```bash
python scripts/combine_and_setup_data.py
```

## Download Scripts

### `download_with_ai.py`
Use AI agent to help download OSHA data files.

```bash
python scripts/download_with_ai.py --api-key YOUR_API_KEY
```

See [docs/AI_DOWNLOAD_GUIDE.md](../docs/AI_DOWNLOAD_GUIDE.md) for details.

### `download_data_helper.py`
Helper utilities for downloading data (used by other scripts).

## Testing & Examples

### `test_amazon.py`
Test script for Amazon compliance analysis using all features.

```bash
python scripts/test_amazon.py
```

See [docs/RUN_AMAZON_TEST.md](../docs/RUN_AMAZON_TEST.md) for details.

### `example_db_usage.py`
Example script demonstrating database usage.

```bash
python scripts/example_db_usage.py
```

## Shell Scripts

### `run_ai_download.sh`
Shell script wrapper for AI-powered downloads.

```bash
bash scripts/run_ai_download.sh
```

