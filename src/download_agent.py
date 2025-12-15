"""
AI-Powered Download Agent
Uses ChatGPT/OpenAI to help find and download OSHA data files.
"""

import os
import requests
from pathlib import Path
import zipfile
from typing import List, Dict, Optional, Tuple
import json
from urllib.parse import urljoin, urlparse

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI package not installed. Install with: pip install openai")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


class DownloadAgent:
    """AI-powered agent to help download OSHA data files."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize download agent.
        
        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY environment variable)
            model: OpenAI model to use (default: gpt-4o-mini for cost efficiency)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package required. Install with: pip install openai")
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter"
            )
        
        self.client = OpenAI(api_key=self.api_key)
    
    def search_download_urls(self) -> Dict[str, List[str]]:
        """
        Use AI to search for current OSHA data download URLs.
        
        Returns:
            Dictionary with potential URLs for each data type
        """
        print("🤖 Using AI to search for OSHA data download URLs...")
        print()
        
        prompt = """You are helping to find download URLs for OSHA (Occupational Safety and Health Administration) 
enforcement data files. The U.S. Department of Labor hosts these files.

IMPORTANT: The URLs https://enfxfr.dol.gov/data_catalog/OSHA/ and https://enforcedata.dol.gov/data_catalog/OSHA/ 
are returning 404 errors, meaning the data structure has changed.

Please provide alternative URLs or methods to access:
1. OSHA inspection data (osha_inspection.csv or similar)
2. OSHA violation data (osha_violation.csv or similar)  
3. OSHA accident data (osha_accident.csv or similar)

Consider these sources:
- DOL Enforcement Data Catalog: https://enforcedata.dol.gov/views/data_catalogs.php
- OSHA Data page: https://www.osha.gov/data
- OSHA Severe Injury Reports: https://www.osha.gov/severe-injury-reports
- DOL Enforcement Data downloads page
- FOIA data releases
- Alternative file naming conventions (inspection_data.csv, violations.csv, etc.)

Please respond with a JSON object in this format:
{
  "inspection": ["url1", "url2", ...],
  "violation": ["url1", "url2", ...],
  "accident": ["url1", "url2", ...],
  "instructions": "Step-by-step instructions for manual download if URLs don't work"
}

Include the most likely current URLs based on typical government data portal structures.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that finds government data download URLs. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            urls_dict = json.loads(content)
            
            print("✓ AI suggested URLs:")
            for data_type, urls in urls_dict.items():
                print(f"  {data_type}: {len(urls)} URLs found")
            
            return urls_dict
            
        except Exception as e:
            print(f"✗ Error getting AI suggestions: {e}")
            return {"inspection": [], "violation": [], "accident": []}
    
    def get_download_instructions(self) -> str:
        """
        Get step-by-step download instructions from AI.
        
        Returns:
            Markdown-formatted instructions
        """
        print("🤖 Getting download instructions from AI...")
        
        prompt = """Provide clear, step-by-step instructions for manually downloading OSHA enforcement data 
(inspections, violations, accidents) from the U.S. Department of Labor or OSHA websites.

Include:
1. The exact website URLs to visit
2. Where to find the data catalog
3. Which files to download
4. Where to save them
5. How to verify the download worked

Format the response as clear markdown with numbered steps.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful technical assistant that provides clear, step-by-step instructions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error getting instructions: {e}"
    
    def try_download_urls(self, urls: List[str], filename: str) -> Tuple[bool, Optional[str]]:
        """
        Try to download from a list of URLs.
        
        Returns:
            (success: bool, successful_url: Optional[str])
        """
        for url in urls:
            try:
                print(f"  Trying: {url[:80]}...")
                response = requests.get(url, stream=True, timeout=30, allow_redirects=True)
                
                if response.status_code == 200:
                    filepath = DATA_DIR / filename
                    
                    # Check if it's actually a file or a redirect to a page
                    content_type = response.headers.get('content-type', '')
                    content_length = response.headers.get('content-length')
                    
                    if 'text/html' in content_type and content_length and int(content_length) < 100000:
                        # Likely an HTML page, not a file
                        print(f"    ✗ URL returns HTML page, not a file")
                        continue
                    
                    with open(filepath, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    file_size = filepath.stat().st_size / (1024 * 1024)
                    print(f"    ✓ Successfully downloaded ({file_size:.1f} MB)")
                    
                    return True, url
                else:
                    print(f"    ✗ HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"    ✗ Error: {str(e)[:60]}")
        
        return False, None
    
    def download_with_ai_help(self) -> Dict[str, bool]:
        """
        Use AI to find URLs and attempt downloads.
        
        Returns:
            Dictionary with download status for each file type
        """
        print("=" * 70)
        print("AI-POWERED OSHA DATA DOWNLOAD")
        print("=" * 70)
        print()
        
        # Get AI-suggested URLs
        url_suggestions = self.search_download_urls()
        print()
        
        # Map to our file naming
        file_mapping = {
            "inspection": "osha_inspection.csv.zip",
            "violation": "osha_violation.csv.zip",
            "accident": "osha_accident.csv.zip"
        }
        
        results = {}
        
        # Try to download each file type
        for data_type, urls in url_suggestions.items():
            if not urls:
                print(f"⚠ No URLs found for {data_type} data")
                results[data_type] = False
                continue
            
            filename = file_mapping.get(data_type, f"osha_{data_type}.csv.zip")
            print(f"Downloading {data_type} data...")
            
            success, successful_url = self.try_download_urls(urls, filename)
            
            if success:
                results[data_type] = True
                # Try to extract if it's a zip
                self._extract_if_zip(DATA_DIR / filename)
            else:
                results[data_type] = False
                print(f"  ✗ Could not download {data_type} data from any suggested URL")
            
            print()
        
        # Summary
        print("=" * 70)
        print("Download Summary")
        print("=" * 70)
        for data_type, success in results.items():
            status = "✓" if success else "✗"
            print(f"{status} {data_type}: {'Downloaded' if success else 'Failed'}")
        print()
        
        # Get manual instructions if downloads failed
        if not all(results.values()):
            print("Some downloads failed. Getting manual download instructions...")
            print()
            instructions = self.get_download_instructions()
            print(instructions)
            print()
        
        return results
    
    def _extract_if_zip(self, filepath: Path):
        """Extract zip file if it exists and is a zip."""
        if not filepath.exists():
            return
        
        try:
            # Check if it's a zip file
            with zipfile.ZipFile(filepath, 'r') as z:
                csv_name = filepath.stem  # Remove .zip
                csv_path = DATA_DIR / csv_name
                
                if not csv_path.exists():
                    print(f"  Extracting {filepath.name}...")
                    z.extractall(DATA_DIR)
                    print(f"  ✓ Extracted to {csv_name}")
                    
                    # Remove zip to save space
                    filepath.unlink()
                    print(f"  ✓ Removed zip file")
        except zipfile.BadZipFile:
            # Not a zip file, might already be CSV
            pass
        except Exception as e:
            print(f"  ⚠ Could not extract {filepath.name}: {e}")
    
    def interactive_download(self):
        """Interactive download session with AI assistance."""
        print("=" * 70)
        print("INTERACTIVE AI-POWERED DOWNLOAD")
        print("=" * 70)
        print()
        
        # Check current status
        from .data_loader import get_data_summary
        summary = get_data_summary()
        
        print("Current data status:")
        for name, info in summary.items():
            status = info.get('status', 'unknown')
            if status == 'loaded':
                rows = info.get('rows', 0)
                print(f"  ✓ {name}: {rows:,} rows")
            else:
                print(f"  ✗ {name}: {status}")
        print()
        
        # Ask AI for help
        response = input("Would you like AI to search for download URLs? (y/n): ")
        if response.lower() == 'y':
            self.download_with_ai_help()
        else:
            instructions = self.get_download_instructions()
            print("\nManual Download Instructions:")
            print("=" * 70)
            print(instructions)


def main():
    """Command-line interface for download agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI-powered OSHA data download agent')
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='OpenAI API key (or set OPENAI_API_KEY env var)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='gpt-4o-mini',
        help='OpenAI model to use (default: gpt-4o-mini)'
    )
    parser.add_argument(
        '--instructions-only',
        action='store_true',
        help='Only get instructions, don\'t attempt downloads'
    )
    
    args = parser.parse_args()
    
    try:
        agent = DownloadAgent(api_key=args.api_key, model=args.model)
        
        if args.instructions_only:
            instructions = agent.get_download_instructions()
            print(instructions)
        else:
            agent.download_with_ai_help()
            
    except ValueError as e:
        print(f"Error: {e}")
        print("\nTo use this agent:")
        print("1. Get an OpenAI API key from: https://platform.openai.com/api-keys")
        print("2. Set it as environment variable: export OPENAI_API_KEY='your-key-here'")
        print("3. Or pass with --api-key flag")
    except ImportError as e:
        print(f"Error: {e}")
        print("\nInstall required packages:")
        print("  pip install openai beautifulsoup4")


if __name__ == "__main__":
    main()

