"""
Email generation logic using Gemini AI.
Handles email content generation, parsing, and token usage tracking.
"""

import json
import logging
from typing import Dict
import pandas as pd
from google.cloud import vision
from vertexai.generative_models import GenerativeModel

from .prompts import (
    build_single_email_prompt,
    build_triggered_email_prompt,
    build_image_extraction_prompt,
    build_email_signature
)
from services.supabase_service import get_supabase_client

logger = logging.getLogger(__name__)


class EmailGenerator:
    """
    Handles all email generation operations using Gemini AI.
    Separated from GeminiService for better organization.
    """
    
    def __init__(self, model: GenerativeModel, vision_client=None):
        """
        Initialize email generator with Gemini model.
        
        Args:
            model: Initialized Gemini GenerativeModel instance
            vision_client: Optional Vision API client for image processing
        """
        self.model = model
        self.vision_client = vision_client
    
    def generate_single_email(
        self,
        category_prompt: str,
        campaign_context: Dict[str, str],
        user_id: str = None
    ) -> Dict:
        """
        Generate a single email for a specific category using Vertex AI Gemini.
        
        Args:
            category_prompt: The prompt for this email category
            campaign_context: Dictionary with campaign_name, tone, objective, target_city
        
        Returns:
            Dictionary with 'subject', 'body' keys and 'metadata' with token usage
        """
        prompt = build_single_email_prompt(category_prompt, campaign_context)
        
        # Debug logging
        logger.info(f"CATEGORY: {category_prompt}")
        logger.info(f"AGENT NAME: {campaign_context.get('agent_name')}")
        logger.info(f"COMPANY NAME: {campaign_context.get('company_name')}")
        logger.info(f"TONE: {campaign_context.get('tones')}")
        logger.info(f"OBJECTIVE: {campaign_context.get('objective')}")
        
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
            logger.info(
                f"✅ Generated email | Tokens: {token_info.get('total_tokens', 'N/A')} | "
                f"Input: {token_info.get('input_tokens')} | Output: {token_info.get('output_tokens')}"
            )
            
            # Add metadata to response
            parsed['metadata'] = token_info
            
            return parsed
            
        except Exception as e:
            logger.error(f"❌ Error generating email: {str(e)}")
            raise
    
    async def generate_triggered_email(
        self,
        user_id: str,
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
        try:
            logger.info(
                f"🎯 Generating triggered email for {realtor_name} - "
                f"Purpose: {purpose} - Persona: {persona}"
                f"Short Desc: {short_description}"
            )
            
            prompt = build_triggered_email_prompt(
                realtor_name, brokerage, markets, purpose, persona, short_description
            )
            
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
                    email_content['body'] = f"<p>Dear {{name}},</p><p>{body}</p>"
                
                logger.info("✅ Successfully generated triggered email")
                
                # Append signature if user_id provided
                if user_id:
                    try:
                        supabase = get_supabase_client()
                        profile_response = supabase.table('profiles').select(
                            'phone, email, calendly_link, full_name, years_in_business, '
                            'brokerage_logo_url, brand_logo_url, realtor_type, '
                            'company_name, brokerage_name, markets'
                        ).eq('id', user_id).single().execute()
                        
                        if profile_response.data:
                            phone = profile_response.data.get('phone', '')
                            email_addr = profile_response.data.get('email', '')
                            calendly_link = profile_response.data.get('calendly_link', '')
                            full_name = profile_response.data.get('full_name', '')
                            years = profile_response.data.get('years_in_business', 0)
                            realtor_type = profile_response.data.get('realtor_type', '').lower()
                            company_name = profile_response.data.get('company_name', '')
                            brokerage_name = profile_response.data.get('brokerage_name', '')
                            markets = profile_response.data.get('markets', [])
                            
                            # Logo selection based on realtor type
                            if realtor_type == 'team':
                                logo_url = profile_response.data.get('brand_logo_url', '')
                            else:
                                logo_url = profile_response.data.get('brokerage_logo_url', '')
                            
                            # Display brokerage priority
                            display_brokerage = brokerage_name if brokerage_name else company_name
                            
                            if full_name and phone and email_addr:
                                experience = f"{years}+ years helping clients achieve their real estate goals" if years else None
                                markets_list = markets if isinstance(markets, list) else []
                                
                                signature = build_email_signature(
                                    realtor_name=full_name,
                                    brokerage=display_brokerage,
                                    phone=phone,
                                    email=email_addr,
                                    title="Real Estate Professional",
                                    experience=experience,
                                    markets=markets_list,
                                    calendly_link=calendly_link if calendly_link else None,
                                    logo_url=logo_url if logo_url else None
                                )
                                
                                email_content['body'] = email_content['body'] + signature
                                logger.info("✅ Appended email signature")
                    except Exception as sig_error:
                        logger.warning(f"Could not append signature: {sig_error}")
                
                return email_content
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse email JSON: {e}")
                logger.error(f"Raw response: {clean_response}")
                
                # Fallback response
                markets_str = ", ".join(markets) if markets else "local area"
                return {
                    "subject": f"Important Update from {realtor_name}",
                    "body": (
                        f"<p>Dear {{name}},</p>"
                        f"<p>I hope this message finds you well. I wanted to reach out regarding {purpose.lower()}.</p>"
                        f"<p>As your trusted real estate professional at {brokerage}, "
                        f"I'm committed to keeping you informed about important developments in the {markets_str} market.</p>"
                        f"<p>Please don't hesitate to reach out if you have any questions.</p>"
                        f"<p>Best regards,<br/>{realtor_name}</p>"
                    )
                }
                
        except Exception as e:
            logger.error(f"Error generating triggered email: {e}")
            # Return fallback email
            return {
                "subject": f"Update from {realtor_name}",
                "body": (
                    f"<p>Dear {{name}},</p>"
                    f"<p>I hope you're doing well. I wanted to share some important information with you.</p>"
                    f"<p>Thank you for your continued trust in my services.</p>"
                    f"<p>Best regards,<br/>{realtor_name}<br/>{brokerage}</p>"
                )
            }
    
    def process_image_to_contacts(self, image_bytes: bytes) -> pd.DataFrame:
        """
        Process an image using Google Vision API to extract text,
        then use Gemini to structure the data into contact information.
        
        Args:
            image_bytes: Raw image bytes (JPG, PNG, etc.)
            
        Returns:
            DataFrame with columns: name, email, phone, city, address
        """
        if not self.vision_client:
            raise ValueError("Vision client not initialized")
        
        try:
            # Step 1: Extract text using Vision API
            img = vision.Image(content=image_bytes)
            response = self.vision_client.text_detection(image=img)
            
            if response.error.message:
                raise Exception(f"Vision API error: {response.error.message}")
            
            if not response.text_annotations:
                logger.warning("No text detected in image")
                return pd.DataFrame(columns=["name", "email", "phone", "city", "address"])
            
            extracted_text = response.text_annotations[0].description
            logger.info("✅ Vision API extracted text from image")
            
            # Step 2: Structure the data using Gemini
            prompt = build_image_extraction_prompt(extracted_text)
            output = self.model.generate_content(prompt).text
            logger.info("✅ Gemini structured the contact data")
            
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
    
    def _parse_email_response(self, response_text: str) -> Dict[str, str]:
        """
        Parse Gemini response to extract subject and body.
        
        Args:
            response_text: Raw text response from Gemini
        
        Returns:
            Dictionary with 'subject' and 'body' keys
        """
        try:
            # Clean up response text
            response_text = response_text.strip()
            
            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Try to fix common JSON issues
            if response_text.count('"') % 2 != 0:
                response_text = response_text + '"'
            
            # Remove any trailing incomplete JSON structures
            if not response_text.endswith('}'):
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
        """
        Extract token usage from Gemini response.
        
        Args:
            response: Gemini response object
        
        Returns:
            Dictionary with input_tokens, output_tokens, total_tokens
        """
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
