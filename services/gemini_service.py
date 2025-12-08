"""
Gemini AI Service - Main service class for AI operations.
Delegates email generation to email_generation.py for better organization.
"""

import os
import logging
from typing import Dict, Optional
import pandas as pd
from dotenv import load_dotenv

# Lazy imports for memory optimization
def get_google_vision():
    try:
        from google.cloud import vision
        return vision
    except ImportError:
        logging.warning("Google Cloud Vision not available")
        return None

def get_vertexai():
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        return vertexai, GenerativeModel
    except ImportError:
        logging.warning("VertexAI not available")
        return None, None

def get_email_generator():
    from .email_generation import EmailGenerator
    return EmailGenerator

load_dotenv()

logger = logging.getLogger(__name__)

# Create directory for storing responses (for debugging)
GEMINI_RESPONSES_DIR = os.path.join(os.path.dirname(__file__), "..", "gemini_responses")
os.makedirs(GEMINI_RESPONSES_DIR, exist_ok=True)


class GeminiService:
    """
    Gemini AI Service for generating real estate email content and processing images.
    Uses Vertex AI Gemini models.
    Includes Google Vision API for text extraction from images.
    """
    
    def __init__(self):
        """Initialize service with lazy loading for memory efficiency."""
        self.model = None
        self.vision_client = None
        self.email_generator = None
        self._initialized = False
        self._vertexai = None
        self._GenerativeModel = None
        self._vision = None
        
    def _ensure_initialized(self):
        """Ensure the service is initialized with Google APIs."""
        if self._initialized:
            return
            
        try:
            logger.info("🔧 Initializing Gemini Service with lazy loading...")
            
            # Lazy load dependencies
            self._vertexai, self._GenerativeModel = get_vertexai()
            self._vision = get_google_vision()
            
            if not self._vertexai or not self._GenerativeModel:
                logger.warning("⚠️ VertexAI not available - AI features disabled")
                self._initialized = True
                return
                
            logger.info(f"📍 Current working directory: {os.getcwd()}")
            logger.info(f"🔍 Checking environment variables...")
            logger.info(f"   - GOOGLE_CREDENTIALS_JSON: {'✅ Found' if os.getenv('GOOGLE_CREDENTIALS_JSON') else '❌ Not found'}")
            logger.info(f"   - GOOGLE_APPLICATION_CREDENTIALS: {'✅ Found' if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') else '❌ Not found'}")
            logger.info(f"   - PROJECT_ID: {'✅ Found' if os.getenv('PROJECT_ID') else '❌ Not found'}")
            
            # Handle Google credentials - prioritize JSON for production, file for local
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
                    logger.info("✅ Set Google credentials from GOOGLE_CREDENTIALS_JSON environment variable")
                except json.JSONDecodeError:
                    logger.error("❌ Invalid JSON format in GOOGLE_CREDENTIALS_JSON")
                    raise ValueError("Invalid Google credentials JSON format")
            elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                # Use existing file path (local development)
                creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if os.path.exists(creds_path):
                    logger.info(f"✅ Using Google credentials from file: {creds_path}")
                else:
                    logger.error(f"❌ Google credentials file not found at: {creds_path}")
            else:
                # Fallback to local file for development
                creds_path = os.path.join(os.path.dirname(__file__), "..", "creds", "realtygenie-55126509a168.json")
                if os.path.exists(creds_path):
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
                    logger.info(f"✅ Set Google credentials from local file: {creds_path}")
                else:
                    logger.warning("⚠️ Google credentials not found - some features may not work")
            
            # Initialize Vertex AI
            project_id = os.getenv("PROJECT_ID")
            location = os.getenv("LOCATION")
            
            if not project_id:
                raise ValueError("❌ PROJECT_ID not found")
            
            self._vertexai.init(project=project_id, location=location)
            
            # Initialize Gemini model
            self.model = self._GenerativeModel("gemini-2.5-flash")
            self.image_model = self._GenerativeModel("gemini-2.5-flash-image")
            
            # Initialize Vision API client (only if available)
            if self._vision:
                self.vision_client = self._vision.ImageAnnotatorClient()
            else:
                self.vision_client = None
                logger.warning("⚠️ Google Vision not available - image processing disabled")
            
            # Initialize email generator with model and vision client
            EmailGenerator = get_email_generator()
            self.email_generator = EmailGenerator(self.model, self.vision_client)
            
            self._initialized = True
            logger.info("✅ Vertex AI Gemini and Vision API initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini service: {str(e)}")
            raise ValueError(f"Gemini initialization failed: {str(e)}")
    
    def generate_single_email(
        self,
        category_prompt: str,
        campaign_context: Dict[str, str]
    ) -> Dict:
        """
        Generate a single email for a specific category using Vertex AI Gemini.
        
        Args:
            category_prompt: The prompt for this email category
            campaign_context: Dictionary with campaign_name, tone, objective, target_city
        
        Returns:
            Dictionary with 'subject', 'body' keys and 'metadata' with token usage
        """
        self._ensure_initialized()
        return self.email_generator.generate_single_email(category_prompt, campaign_context)
    
    def process_image(self, image_bytes: bytes) -> pd.DataFrame:
        """
        Process an image using Google Vision API to extract text,
        then use Gemini to structure the data into contact information.
        
        Args:
            image_bytes: Raw image bytes (JPG, PNG, etc.)
            
        Returns:
            DataFrame with columns: name, email, phone, city, address
        """
        self._ensure_initialized()
        return self.email_generator.process_image_to_contacts(image_bytes)

    async def generate_triggered_email(
        self,
        realtor_name: str,
        brokerage: str,
        markets: list,
        purpose: str,
        persona: str,
        short_description: str = None
    ) -> Dict[str, str]:
        """
        Generate personalized email content for triggered emails.
        
        Args:
            realtor_name: Name of the realtor
            brokerage: Realtor's brokerage/company
            markets: List of markets the realtor serves
            purpose: Purpose of the email
            persona: Target persona (buyer, seller, investor, past_client, referral, cold_prospect)
            short_description: Optional additional context
        
        Returns:
            Dictionary with 'subject' and 'body' keys
        """
        self._ensure_initialized()
        return await self.email_generator.generate_triggered_email(
            realtor_name, brokerage, markets, purpose, persona, short_description
        )


_gemini_service_instance = None

def get_gemini_service() -> GeminiService:
    """Get or create Gemini service singleton."""
    global _gemini_service_instance
    
    if _gemini_service_instance is None:
        try:
            _gemini_service_instance = GeminiService()
        except Exception as e:
            logger.error(f"Failed to initialize Gemini service: {str(e)}")
            raise
    
    return _gemini_service_instance

# Alias for vision service
def get_vision_service() -> GeminiService:
    """Get Gemini service (includes vision capabilities)."""
    return get_gemini_service()
