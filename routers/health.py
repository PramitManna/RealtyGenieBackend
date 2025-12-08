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
async def trigger_festive_emails():
    """Manually trigger festive email sending (for testing)"""
    try:
        logger.info("Manually triggering festive email job")
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
