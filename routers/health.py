from fastapi import APIRouter
from datetime import datetime
from services.cron_service import send_pending_emails, send_festive_emails, get_queue_health
import logging

router = APIRouter(prefix="/api", tags=["health"])
logger = logging.getLogger(__name__)

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "RealtyGenie Backend"
    }

@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "RealtyGenie Backend API",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /api/health",
            "clean_leads": "POST /api/leads/clean",
            "validate_single": "POST /api/leads/validate-single",
            "validate_batch": "POST /api/leads/validate-batch",
        }
    }


@router.post("/cron/send-emails")
async def trigger_cron_emails():
    """Manually trigger the email sending cron job (for testing)"""
    try:
        logger.info("Manually triggering email cron job")
        stats = await send_pending_emails()
        return {
            "success": True,
            "message": "Cron job executed",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error in manual cron trigger: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/cron/send-festive-emails")
async def trigger_festive_emails(test_date: str = None):
    """
    Manually trigger festive email sending (for testing)
    
    Args:
        test_date: Optional date in format "MM-DD" to simulate (e.g., "12-25" for Christmas)
    """
    try:
        logger.info(f"Manually triggering festive email job{f' with test date {test_date}' if test_date else ''}")
        
        if test_date:
            # Parse test date and temporarily override the date checking in cron_service
            from datetime import datetime
            try:
                month, day = map(int, test_date.split('-'))
                logger.info(f"Testing with simulated date: Month {month}, Day {day}")
                # We'll pass this to the function
                stats = await send_festive_emails(test_month=month, test_day=day)
            except ValueError:
                return {
                    "success": False,
                    "error": "Invalid test_date format. Use MM-DD (e.g., 12-25)"
                }
        else:
            stats = await send_festive_emails()
        
        return {
            "success": True,
            "message": "Festive email job executed",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error in festive email trigger: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/queue-health")
async def check_queue_health():
    """Check the health status of the email queue"""
    return get_queue_health()
