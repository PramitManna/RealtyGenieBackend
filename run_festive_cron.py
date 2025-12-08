#!/usr/bin/env python3
"""
Festive Email Cron Job Runner
Runs daily to check for festivals and send automated greeting emails

Usage:
    python run_festive_cron.py

Or via cron:
    0 9 * * * cd /path/to/realtygeniebackend2 && /path/to/venv/bin/python run_festive_cron.py >> logs/festive_cron.log 2>&1
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.cron_service import send_festive_emails

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(project_root / 'logs' / 'festive_cron.log', mode='a')
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main execution function"""
    logger.info("=" * 80)
    logger.info(f"🎉 Starting festive email cron job - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    try:
        # Run the festive email sending function
        stats = await send_festive_emails()
        
        # Log results
        logger.info("📊 Festive Email Cron Job Results:")
        logger.info(f"   Festivals checked: {', '.join(stats['checked_festivals']) if stats['checked_festivals'] else 'None today'}")
        logger.info(f"   Emails sent: {stats['emails_sent']}")
        logger.info(f"   Emails failed: {stats['emails_failed']}")
        
        if stats['errors']:
            logger.error(f"   Errors encountered: {len(stats['errors'])}")
            for error in stats['errors'][:5]:  # Log first 5 errors
                logger.error(f"      - {error}")
        
        logger.info("✅ Festive email cron job completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Festive email cron job failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
