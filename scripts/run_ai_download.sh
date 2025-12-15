#!/bin/bash
# Quick script to run AI download agent

echo "OSHA Data Download - AI Assisted"
echo "================================"
echo ""

# Check if API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠ OpenAI API key not found in environment."
    echo ""
    read -p "Enter your OpenAI API key: " api_key
    export OPENAI_API_KEY="$api_key"
    echo ""
fi

# Run the download agent
python3 download_with_ai.py

