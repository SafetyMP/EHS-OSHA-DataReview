"""
AI-Powered Download Helper Script
Uses ChatGPT to help find and download OSHA data files.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.download_agent import DownloadAgent
except ImportError as e:
    print("=" * 70)
    print("SETUP REQUIRED")
    print("=" * 70)
    print()
    print("To use the AI download agent:")
    print()
    print("1. Install required packages:")
    print("   pip install openai beautifulsoup4")
    print()
    print("2. Get an OpenAI API key:")
    print("   Visit: https://platform.openai.com/api-keys")
    print("   Create a new API key")
    print()
    print("3. Set the API key as environment variable:")
    print("   export OPENAI_API_KEY='your-key-here'")
    print()
    print("   Or pass it directly:")
    print("   python download_with_ai.py --api-key 'your-key-here'")
    print()
    print("Error:", str(e))
    sys.exit(1)


def main():
    """Main function."""
    import os
    import sys
    
    print("=" * 70)
    print("OSHA DATA DOWNLOAD - AI ASSISTED")
    print("=" * 70)
    print()
    
    # Check for API key from command line argument
    api_key = None
    if len(sys.argv) > 1:
        if sys.argv[1] == '--api-key' and len(sys.argv) > 2:
            api_key = sys.argv[2]
        elif sys.argv[1].startswith('sk-'):
            # Assume first arg is the API key
            api_key = sys.argv[1]
    
    # Check environment variable
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    
    # Prompt if still not found (only if interactive)
    if not api_key:
        print("⚠ OpenAI API key not found.")
        print()
        print("Usage options:")
        print("  1. Set environment variable: export OPENAI_API_KEY='your-key'")
        print("  2. Pass as argument: python download_with_ai.py 'your-key'")
        print("  3. Pass with flag: python download_with_ai.py --api-key 'your-key'")
        print()
        
        # Only prompt if stdin is a TTY (interactive)
        if sys.stdin.isatty():
            try:
                response = input("Enter your OpenAI API key (or 'q' to quit): ").strip()
                if response.lower() == 'q':
                    return
                api_key = response
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled.")
                return
        else:
            print("Not running interactively. Please provide API key via environment variable or argument.")
            return
        
        if not api_key:
            print("No API key provided. Exiting.")
            return
    
    try:
        # Initialize agent
        print("Initializing AI agent...")
        agent = DownloadAgent(api_key=api_key)
        print("✓ Agent ready")
        print()
        
        # Run download
        agent.download_with_ai_help()
        
        # Check results
        print()
        print("=" * 70)
        print("VERIFICATION")
        print("=" * 70)
        
        from src.data_loader import get_data_summary
        summary = get_data_summary()
        
        all_loaded = True
        for name, info in summary.items():
            if info.get('status') == 'loaded':
                rows = info.get('rows', 0)
                print(f"✓ {name}: {rows:,} rows")
            else:
                print(f"✗ {name}: {info.get('status', 'unknown')}")
                all_loaded = False
        
        print()
        if all_loaded:
            print("🎉 All data files are ready!")
            print()
            print("Next steps:")
            print("  1. Test: python3 test_amazon.py")
            print("  2. Launch dashboard: streamlit run app.py")
        else:
            print("Some files are still missing.")
            print("The AI agent has provided manual download instructions above.")
            print("Or check DATA_DOWNLOAD_GUIDE.md for more help.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

