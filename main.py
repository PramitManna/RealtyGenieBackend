from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from dotenv import load_dotenv
import os

# Load environment variables FIRST
load_dotenv()

# Debug environment variables at startup
logging.basicConfig(level=logging.INFO)
logging.info("🚀 Starting RealtyGenie Backend...")
logging.info(f"📍 Current working directory: {os.getcwd()}")
logging.info("🔍 Environment Variables Check:")
logging.info(f"   - GOOGLE_CREDENTIALS_JSON: {'✅ Found' if os.getenv('GOOGLE_CREDENTIALS_JSON') else '❌ Not found'}")
logging.info(f"   - GOOGLE_APPLICATION_CREDENTIALS: {'✅ Found' if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') else '❌ Not found'}")
logging.info(f"   - PROJECT_ID: {'✅ Found' if os.getenv('PROJECT_ID') else '❌ Not found'}")
logging.info(f"   - SUPABASE_URL: {'✅ Found' if os.getenv('SUPABASE_URL') else '❌ Not found'}")
logging.info(f"   - MAILGUN_API_KEY: {'✅ Found' if os.getenv('MAILGUN_API_KEY') else '❌ Not found'}")

# Set Google Application Credentials - prioritize production JSON method
google_creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if google_creds_json:
    # Production deployment with JSON credentials
    import tempfile
    import json
    try:
        # Validate JSON format
        json.loads(google_creds_json)
        # Create temporary file with credentials
        temp_creds = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        temp_creds.write(google_creds_json)
        temp_creds.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_creds.name
        logging.info("✅ Google credentials loaded from GOOGLE_CREDENTIALS_JSON environment variable")
    except json.JSONDecodeError:
        logging.error("❌ Invalid JSON format in GOOGLE_CREDENTIALS_JSON")
elif not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    # Fallback to local file for development
    creds_path = os.path.join(os.path.dirname(__file__), "creds", "realtygenie-55126509a168.json")
    if os.path.exists(creds_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
        logging.info(f"✅ Google credentials loaded from local file: {creds_path}")
    else:
        logging.warning("⚠️ Google credentials not found - some features may not work")
else:
    logging.info(f"✅ Google credentials already set: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")

# Verify Supabase credentials are loaded
if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
    raise ValueError("❌ SUPABASE_URL and SUPABASE_KEY must be set in .env file")

# Now import routers that depend on environment variables
from routers import leads, batches, health, campaigns, campaign_emails
from routers.lead_nurture import router as lead_nurture_router

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
