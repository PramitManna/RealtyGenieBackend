from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api", tags=["health"])

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
