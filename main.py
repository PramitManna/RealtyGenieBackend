from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from dotenv import load_dotenv
import os

# Load environment variables FIRST
load_dotenv()

# Set Google Application Credentials if not already set
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    creds_path = os.path.join(os.path.dirname(__file__), "creds", "realtygenie-55126509a168.json")
    if os.path.exists(creds_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
        logging.info(f"✅ Set Google credentials: {creds_path}")
    else:
        logging.warning("⚠️ Google credentials file not found - some features may not work")

# Verify Supabase credentials are loaded
if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
    raise ValueError("❌ SUPABASE_URL and SUPABASE_KEY must be set in .env file")

# Now import routers that depend on environment variables
from routers import leads, batches, health, campaigns, campaign_emails
from routers.lead_nurture import router as lead_nurture_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("✅ RealtyGenie Backend API started")
    yield
    logger.info("🛑 RealtyGenie Backend API shutdown")

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

app.include_router(health.router)
app.include_router(leads.router)
app.include_router(batches.router)
app.include_router(campaigns.router)
app.include_router(campaign_emails.router)
app.include_router(lead_nurture_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
