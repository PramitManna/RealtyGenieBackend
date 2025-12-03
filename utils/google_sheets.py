import re
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)


def extract_sheet_id(url: str) -> Optional[str]:
    """    
    Supports:
    - https://docs.google.com/spreadsheets/d/{ID}/edit
    - https://docs.google.com/spreadsheets/d/{ID}/edit#gid=0
    - https://docs.google.com/spreadsheets/d/{ID}
    
    Args:
        url: Google Sheets URL
        
    Returns:
        Sheet ID or None if URL is invalid
    """
    try:
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, url)
        
        if match:
            sheet_id = match.group(1)
            logger.info(f"✅ Extracted sheet ID: {sheet_id[:20]}...")
            return sheet_id
        else:
            logger.error(f"❌ Invalid Google Sheets URL format: {url}")
            return None
    except Exception as e:
        logger.error(f"❌ Error extracting sheet ID: {e}")
        return None


def fetch_google_sheet_as_csv(url: str, timeout: int = 30) -> Optional[bytes]:
    """
    Fetch Google Sheets as CSV using gviz query (no authentication required)
    Works with "Anyone with the link" shared sheets
    
    Args:
        url: Google Sheets URL
        timeout: Request timeout in seconds
        
    Returns:
        CSV data as bytes or None if failed
    """
    try:
        sheet_id = extract_sheet_id(url)
        if not sheet_id:
            logger.error("Failed to extract sheet ID from URL")
            return None
        
        logger.info(f"📥 Fetching Google Sheets as CSV using gviz...")
        
        gviz_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        session = requests.Session()
        response = session.get(gviz_url, headers=headers, timeout=timeout, allow_redirects=True)
        
        if response.status_code == 200:
            logger.info(f"✅ Successfully fetched {len(response.content)} bytes from Google Sheets (gviz)")
            return response.content
        else:
            logger.error(f"❌ Failed to fetch Google Sheet: HTTP {response.status_code}")
            return None
    
    except requests.Timeout:
        logger.error(f"⏱️  Timeout fetching Google Sheets (>{timeout}s)")
        return None
    except requests.RequestException as e:
        logger.error(f"❌ HTTP error fetching Google Sheets: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error fetching Google Sheets: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
