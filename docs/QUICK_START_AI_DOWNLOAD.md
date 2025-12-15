# Quick Start: AI-Powered Download

Since you have the API key, here are the quickest ways to run the download:

## Option 1: Set Environment Variable (Recommended)

```bash
export OPENAI_API_KEY='your-api-key-here'
python3 download_with_ai.py
```

## Option 2: Pass API Key Directly

```bash
python3 download_with_ai.py 'your-api-key-here'
```

Or with flag:

```bash
python3 download_with_ai.py --api-key 'your-api-key-here'
```

## Option 3: Use the Shell Script

```bash
./run_ai_download.sh
```

(It will prompt for the key if not set)

## What Happens Next

1. AI searches for current OSHA data URLs
2. Tests each URL to find working ones
3. Downloads files automatically
4. Extracts ZIP files
5. Verifies downloads

## After Download

Once files are downloaded:

```bash
# Check status
python3 check_data_status.py

# Test loading
python3 src/data_loader.py

# Test with Amazon
python3 scripts/test_amazon.py

# Launch dashboard
streamlit run app.py
```

