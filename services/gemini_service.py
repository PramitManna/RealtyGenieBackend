import os
import json
import logging
from typing import Dict
from datetime import datetime
from google.cloud import vision
from vertexai.generative_models import GenerativeModel
import vertexai
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Create directory for storing responses (for debugging)
GEMINI_RESPONSES_DIR = os.path.join(os.path.dirname(__file__), "..", "gemini_responses")
os.makedirs(GEMINI_RESPONSES_DIR, exist_ok=True)

# Premium color palette for emails
PREMIUM_COLORS = {
    "primary": "#1a1a1a",      # Dark charcoal
    "accent": "#d4af37",        # Gold
    "text": "#333333",          # Near black
    "light": "#f8f8f8",         # Off white
    "success": "#2ecc71",       # Green
    "highlight": "#e74c3c",     # Red accent
}


class GeminiService:
    """
    Gemini AI Service for generating real estate email content and processing images.
    Uses Vertex AI Gemini models.
    Includes Google Vision API for text extraction from images.
    """
    
    def __init__(self):
        """Initialize service without connecting to Google APIs yet."""
        self.model = None
        self.vision_client = None
        self._initialized = False
        
    def _ensure_initialized(self):
        """Ensure the service is initialized with Google APIs."""
        if self._initialized:
            return
            
        try:
            logger.info("🔧 Initializing Gemini Service...")
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
            
            vertexai.init(project=project_id, location=location)
            
            # Initialize Gemini model
            self.model = GenerativeModel("gemini-2.5-flash")
            
            # Initialize Vision API client
            self.vision_client = vision.ImageAnnotatorClient()
            
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
        prompt = self._build_single_email_prompt(category_prompt, campaign_context)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                }
            )
            
            parsed = self._parse_email_response(response.text)
            
            # Extract token usage metadata
            token_info = self._extract_token_usage(response)
            logger.info(f"✅ Generated email | Tokens: {token_info.get('total_tokens', 'N/A')} | Input: {token_info.get('input_tokens')} | Output: {token_info.get('output_tokens')}")
            
            # Add metadata to response
            parsed['metadata'] = token_info
            
            return parsed
            
        except Exception as e:
            logger.error(f"❌ Error generating email: {str(e)}")
            raise
    
    def _build_single_email_prompt(
        self,
        category_prompt: str,
        context: Dict[str, str]
    ) -> str:
        """Build optimized prompt for generating premium HTML emails with blended user tones."""
        
        current_year = datetime.now().year
        agent_name = context.get('agent_name', 'Real Estate Professional')
        company_name = context.get('company_name', 'Realty Company')
        tone = context.get('tones', 'professional')
        objective = context.get('objective', 'lead nurturing')
        target_city = context.get('target_city', 'your market')
        tone_instruction = ""

        print("CATEGORY : ", category_prompt)
        print("AGENT NAME : ", agent_name)
        print("COMPANY NAME : ", company_name)
        print("TONE : ", tone)
        print("OBJECTIVE : ", objective)
        print("CURRENT YEAR : ", current_year)
        
        # Handle tone blending
        tones_array = context.get('tones_array', [])
        if isinstance(tones_array, list) and len(tones_array) > 1:
            tone_instruction = f"""Blend these communication tones harmoniously: {', '.join(tones_array)}
- Balance all tones naturally without contradicting each other
- Create a cohesive voice that incorporates the best qualities of each tone
- Primary tone is '{tone}' but incorporate elements from: {', '.join(tones_array[1:])}"""
        else:
            tone_instruction = f"Use {tone} language and style throughout"
        print(tone_instruction)        
        return f"""You are a premium real estate email expert. Generate a highly professional, concise email.

**EMAIL CONTEXT**:
- Category: {category_prompt}
- Agent: {agent_name} | Company: {company_name}
- Target Market: {target_city}
- Tone: {tone_instruction}
- Objective: {objective}
- Year: {current_year}

**REQUIREMENTS**:
- Word count: Exactly 100-150 words (concise & impactful)
- Use HTML for rich formatting: <h1>, <h3>, <strong>, <em>, <br/>, <p style="margin:...">
- Premium look: Bold key phrases, use larger font for headlines
- Replace placeholders: {{{{recipient_name}}}}, {{{{city}}}}, {{{{company}}}}, {{{{agent_name}}}}, {{{{year}}}}
- NO markdown, NO code blocks
- Subject line must be compelling and personalized
- Include a clear call-to-action
- Professional but warm tone

**HTML STYLE GUIDE**:
- Title: <h1>
- Headlines: <h3 style="color:#d4af37; font-weight:bold; margin:0 0 10px 0;">
- Important words: <strong style="color:#d4af37;">
- Body text: Regular dark text

**CRITICAL INSTRUCTION**:
- DO NOT include email signature, closing, or sign-off (no "Best regards", "Sincerely", etc.)
- DO NOT add agent name or company name at the end
- Email signature will be automatically appended by the system
- End the email content with the call-to-action or final sentence only

**OUTPUT FORMAT** (return ONLY valid JSON):
{{
  "subject": "Subject line here",
  "body": "<h3 style=\\"color:#d4af37; font-weight:bold; margin:0 0 10px 0;\\">Greeting</h3><p>Body with <strong style=\\"color:#d4af37;\\">emphasized words</strong> in premium gold.</p><p>Call to action here.</p>"
}}

Generate the premium HTML email now:"""
    
    
    def _parse_email_response(self, response_text: str) -> Dict[str, str]:
        """Parse Gemini response to extract subject and body."""
        
        try:
            # Clean up response text
            response_text = response_text.strip()
            
            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Try to fix common JSON issues
            # If JSON is truncated, try to close it
            if response_text.count('"') % 2 != 0:
                response_text = response_text + '"'
            
            # Remove any trailing incomplete JSON structures
            if not response_text.endswith('}'):
                # Find the last complete closing brace
                last_brace = response_text.rfind('}')
                if last_brace > 0:
                    response_text = response_text[:last_brace + 1]
                else:
                    raise ValueError("No closing brace found in response")
            
            # Parse JSON
            data = json.loads(response_text)
            
            # Validate required fields
            if "subject" not in data or "body" not in data:
                raise ValueError("Response missing 'subject' or 'body'")
            
            return {
                "subject": str(data["subject"]).strip(),
                "body": str(data["body"]).strip()
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON: {str(e)}")
            logger.error(f"Response: {response_text[:500]}")
            raise ValueError(f"Invalid JSON response: {str(e)}")
    
    def _extract_token_usage(self, response) -> Dict:
        """Extract token usage from Gemini response."""
        
        try:
            usage_metadata = getattr(response, 'usage_metadata', None)
            
            if usage_metadata:
                input_tokens = getattr(usage_metadata, 'prompt_token_count', 0)
                output_tokens = getattr(usage_metadata, 'candidates_token_count', 0)
                total_tokens = input_tokens + output_tokens
            else:
                # Estimate based on response length
                total_tokens = len(response.text) // 4
                input_tokens = 0
                output_tokens = total_tokens
            
            return {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens
            }
        except Exception as e:
            logger.warning(f"Could not extract token usage: {e}")
            return {"total_tokens": 0}
    
    def process_image(self, image_bytes: bytes) -> pd.DataFrame:
        """
        Process an image using Google Vision API to extract text,
        then use Gemini to structure the data into contact information.
        
        Args:
            image_bytes: Raw image bytes (JPG, PNG, etc.)
            
        Returns:
            DataFrame with columns: name, email, phone, city, address
        """
        try:
            self._ensure_initialized()
            # Step 1: Extract text using Vision API
            img = vision.Image(content=image_bytes)
            response = self.vision_client.text_detection(image=img)
            
            if response.error.message:
                raise Exception(f"Vision API error: {response.error.message}")
            
            if not response.text_annotations:
                logger.warning("No text detected in image")
                return pd.DataFrame(columns=["name", "email", "phone", "city", "address"])
            
            text = response.text_annotations[0].description
            logger.info(f"✅ Vision API extracted text from image")
            
            # Step 2: Structure the data using Gemini
            prompt = f"""
Extract structured contact information from this document text.
Return a JSON array of objects with these fields: name, email, phone, city, address

Rules:
- If a field is not found, set it to null
- Extract ALL contacts found in the document
- Ensure emails are valid format
- Phone numbers should include country/area codes if present
- City should be extracted from addresses when possible

Document text:
{text}

Return ONLY the JSON array, no other text or markdown.
"""
            
            output = self.model.generate_content(prompt).text
            logger.info(f"✅ Gemini structured the contact data")
            
            # Clean and parse JSON
            clean_json = output.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            
            # Convert to DataFrame
            if isinstance(data, dict):
                data = [data]
            
            df = pd.DataFrame(data)
            
            # Ensure all required columns exist
            required_columns = ["name", "email", "phone", "city", "address"]
            for col in required_columns:
                if col not in df.columns:
                    df[col] = None
            
            df = df[required_columns]
            logger.info(f"✅ Extracted {len(df)} contacts from image")
            
            return df
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini output as JSON: {e}")
            logger.error(f"Raw output: {output if 'output' in locals() else 'N/A'}")
            raise Exception("Failed to structure contact data. Please try a clearer image.")
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise

    async def generate_triggered_email(
        self,
        realtor_name: str,
        brokerage: str,
        markets: list,
        purpose: str,
        tones: list,
        short_description: str = None
    ) -> Dict[str, str]:
        """
        Generate personalized email content for triggered emails
        
        Args:
            realtor_name: Name of the realtor
            brokerage: Realtor's brokerage/company
            markets: List of markets the realtor serves
            purpose: Purpose of the email
            tones: List of desired tones
            short_description: Optional additional context
        
        Returns:
            Dictionary with 'subject' and 'body' keys
        """
        try:
            self._ensure_initialized()
            logger.info(f"🎯 Generating triggered email for {realtor_name} - Purpose: {purpose}")
            
            # Build the structured prompt
            markets_str = ", ".join(markets) if markets else "local area"
            tones_str = ", ".join(tones)
            
            prompt = f"""
You are an expert email marketing specialist for real estate professionals. Generate a personalized email for a realtor to send to their leads.

REALTOR DETAILS:
- Name: {realtor_name}
- Brokerage: {brokerage}
- Markets: {markets_str}

EMAIL REQUIREMENTS:
- Purpose: {purpose}
- Tone(s): {tones_str}
- Additional Context: {short_description or "None provided"}

CRITICAL REQUIREMENTS:
1. Must include {{name}} placeholder in the body for personalization
2. Subject line should be compelling and align with the purpose
3. Email must be professional and trust-building
4. Content should be relevant to real estate clients
5. Maintain the selected tone(s) throughout
6. Keep the email concise but impactful (200-400 words)
7. Include a subtle call-to-action when appropriate

FORMATTING RULES:
- Return ONLY the JSON structure below
- No markdown formatting, explanations, or additional text
- Ensure the body uses proper HTML formatting with <p>, <br/>, etc.

RETURN FORMAT:
{{
"subject": "Your compelling subject line here",
"body": "Your email body here with {{name}} placeholder and proper HTML formatting"
}}
"""

            # Generate content
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            logger.info(f"📧 Generated email content for purpose: {purpose}")
            
            # Clean and parse JSON response
            clean_response = response_text.replace("```json", "").replace("```", "").strip()
            
            try:
                email_content = json.loads(clean_response)
                
                # Validate required fields
                if not email_content.get('subject') or not email_content.get('body'):
                    raise ValueError("Missing required subject or body fields")
                
                # Validate that {name} placeholder exists in body
                if '{name}' not in email_content.get('body', ''):
                    logger.warning("Generated email missing {name} placeholder - adding it")
                    body = email_content['body']
                    # Add greeting with placeholder at the beginning
                    email_content['body'] = f"<p>Dear {{name}},</p><p>{body}</p>"
                
                logger.info(f"✅ Successfully generated triggered email")
                return email_content
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse email JSON: {e}")
                logger.error(f"Raw response: {clean_response}")
                
                # Fallback response
                return {
                    "subject": f"Important Update from {realtor_name}",
                    "body": f"<p>Dear {{name}},</p><p>I hope this message finds you well. I wanted to reach out regarding {purpose.lower()}.</p><p>As your trusted real estate professional at {brokerage}, I'm committed to keeping you informed about important developments in the {markets_str} market.</p><p>Please don't hesitate to reach out if you have any questions.</p><p>Best regards,<br/>{realtor_name}</p>"
                }
                
        except Exception as e:
            logger.error(f"Error generating triggered email: {e}")
            # Return fallback email
            return {
                "subject": f"Update from {realtor_name}",
                "body": f"<p>Dear {{name}},</p><p>I hope you're doing well. I wanted to share some important information with you.</p><p>Thank you for your continued trust in my services.</p><p>Best regards,<br/>{realtor_name}<br/>{brokerage}</p>"
            }


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
