# AI-Powered Download Guide

This guide explains how to use the ChatGPT-powered agent to help download OSHA data files.

## Overview

The AI download agent uses OpenAI's API to:
- Search for current OSHA data download URLs
- Test multiple URLs to find working ones
- Provide step-by-step download instructions
- Guide you through the download process

## Setup

### 1. Install Required Packages

```bash
pip install openai beautifulsoup4
```

Or update all dependencies:

```bash
pip install -r requirements.txt
```

### 2. Get OpenAI API Key

1. Visit: https://platform.openai.com/api-keys
2. Sign up or log in
3. Create a new API key
4. Copy the key (starts with `sk-...`)

### 3. Set API Key

**Option A: Environment Variable (Recommended)**
```bash
export OPENAI_API_KEY='your-api-key-here'
```

**Option B: Pass as Parameter**
```bash
python scripts/download_with_ai.py --api-key 'your-api-key-here'
```

**Option C: Enter When Prompted**
The script will ask for it if not found in environment.

## Usage

### Basic Usage

```bash
python scripts/download_with_ai.py
```

The agent will:
1. Search for current download URLs using AI
2. Test each URL to find working ones
3. Download files automatically if found
4. Provide manual instructions if downloads fail

### Get Instructions Only

If you just want instructions without attempting downloads:

```bash
python scripts/download_with_ai.py --instructions-only
```

### Using the Agent in Code

```python
from src.download_agent import DownloadAgent

# Initialize with API key
agent = DownloadAgent(api_key="your-api-key")

# Search for URLs
urls = agent.search_download_urls()
print(urls)

# Get download instructions
instructions = agent.get_download_instructions()
print(instructions)

# Attempt downloads
results = agent.download_with_ai_help()
```

## What the Agent Does

1. **AI Search**: Uses ChatGPT to find current download URLs based on:
   - Knowledge of DOL/OSHA data structure
   - Common data catalog patterns
   - Government website structures

2. **URL Testing**: Tests each suggested URL:
   - Checks HTTP status codes
   - Verifies file types (not HTML pages)
   - Downloads and verifies file sizes

3. **Automatic Extraction**: Extracts ZIP files automatically

4. **Fallback Instructions**: If downloads fail, provides detailed manual instructions

## Example Output

```
======================================================================
AI-POWERED OSHA DATA DOWNLOAD
======================================================================

🤖 Using AI to search for OSHA data download URLs...

✓ AI suggested URLs:
  inspection: 3 URLs found
  violation: 3 URLs found
  accident: 3 URLs found

Downloading inspection data...
  Trying: https://enforcedata.dol.gov/data_catalog/OSHA/osha_inspection.csv.zip...
    ✓ Successfully downloaded (125.3 MB)
  Extracting osha_inspection.csv.zip...
  ✓ Extracted to osha_inspection.csv
  ✓ Removed zip file

...
```

## Cost Considerations

The agent uses OpenAI's API, which has usage costs:
- **gpt-4o-mini**: ~$0.15 per 1M input tokens, $0.60 per 1M output tokens
- Typical usage: <$0.01 per search session
- You can control costs by using `gpt-4o-mini` (default, cheapest)

To change the model:
```python
agent = DownloadAgent(api_key="your-key", model="gpt-4")  # More expensive but more capable
```

## Troubleshooting

### API Key Issues

**Error: "OpenAI API key required"**
- Make sure you've set the environment variable correctly
- Check for typos in the API key
- Verify the key is active on OpenAI's platform

### Download Failures

If AI can't find working URLs:
- The agent will provide manual download instructions
- Check DATA_DOWNLOAD_GUIDE.md for alternative methods
- URLs may have changed - use the instructions to find current ones

### Rate Limits

If you hit OpenAI rate limits:
- Wait a few minutes and try again
- Check your OpenAI usage dashboard
- Consider using a different model

### Import Errors

**Error: "No module named 'openai'"**
```bash
pip install openai beautifulsoup4
```

## Privacy & Security

- Your API key is only used to communicate with OpenAI
- URLs searched are publicly available government data
- No sensitive data is sent to OpenAI
- API key should be kept secret (use environment variables)

## Alternative: Manual Download

If you prefer not to use AI:
1. See `DATA_DOWNLOAD_GUIDE.md` for manual instructions
2. Visit: https://enforcedata.dol.gov/views/data_catalogs.php
3. Download files manually

## Next Steps

After successful download:
1. Verify files: `python3 check_data_status.py`
2. Test loading: `python3 src/data_loader.py`
3. Migrate to database: `python3 -m src.db_migration`
4. Test with Amazon: `python3 scripts/test_amazon.py`
5. Launch dashboard: `streamlit run app.py`

