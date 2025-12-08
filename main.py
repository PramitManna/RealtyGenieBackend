from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from dotenv import load_dotenv
import os
import gc

# Load environment variables FIRST
load_dotenv()

# Setup logging with memory optimization
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Verify Supabase credentials are loaded
if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
    raise ValueError("❌ SUPABASE_URL and SUPABASE_KEY must be set in .env file")

logger.info("🚀 Starting RealtyGenie Backend...")
logger.info(f"📍 Current working directory: {os.getcwd()}")

# Lazy import routers to reduce memory footprint
def get_routers():
    from routers import leads, batches, health, campaigns, campaign_emails
    from routers.lead_nurture import router as lead_nurture_router
    return leads, batches, health, campaigns, campaign_emails, lead_nurture_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("✅ RealtyGenie Backend API started")
    # Force garbage collection on startup
    gc.collect()
    yield
    logger.info("🛑 RealtyGenie Backend API shutdown")
    gc.collect()

app = FastAPI(
    title="RealtyGenie Backend API",
    version="1.0.0",
    description="Lead data cleaning and validation API",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers with lazy loading
leads, batches, health, campaigns, campaign_emails, lead_nurture_router = get_routers()

app.include_router(health.router)
app.include_router(leads.router)
app.include_router(batches.router)
app.include_router(campaigns.router)
app.include_router(campaign_emails.router)
app.include_router(lead_nurture_router)

# Force garbage collection after router registration
gc.collect()
logger.info("🎯 All routers registered, memory optimized")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
