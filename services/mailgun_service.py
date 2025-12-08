import os
import logging
import requests
import re
from typing import Optional, Dict, List
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


class MailgunService:
    """Service for sending emails via Mailgun using requests library"""
    
    def __init__(self):
        self.api_key = os.getenv("MAILGUN_API_KEY")
        self.domain = os.getenv("MAILGUN_DOMAIN")
        self.sender_email = os.getenv("MAILGUN_SENDER_EMAIL", f"Realty Genie <postmaster@{os.getenv('MAILGUN_DOMAIN', 'rg.realtygenie.co')}>")
        
        if not self.api_key or not self.domain:
            raise ValueError("❌ MAILGUN_API_KEY and MAILGUN_DOMAIN not set in .env")
        
        # Mailgun API endpoint
        self.api_url = f"https://api.mailgun.net/v3/{self.domain}/messages"
        
        # Auth credentials
        self.auth = ("api", self.api_key)
        
        logger.info(f"✅ Mailgun service initialized for domain: {self.domain}")
    
    def send_email(
        self,
        to_email: str,
        to_name: Optional[str] = None,
        subject: str = "",
        html_body: str = "",
        text_body: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        tracking: bool = True,
    ) -> Dict:
        """
        Send an email via Mailgun REST API
        
        Args:
            to_email: Recipient email address
            to_name: Recipient name (optional)
            subject: Email subject
            html_body: Email body in HTML format
            text_body: Email body in plain text (optional, auto-generated if not provided)
            reply_to: Reply-to email address (optional)
            cc: List of CC email addresses (optional)
            bcc: List of BCC email addresses (optional)
            tags: List of tags for tracking (optional)
            tracking: Enable open/click tracking (default: True)
        
        Returns:
            Response dict with message_id and status
        """
        try:
            if to_name:
                recipient = f"{to_name} <{to_email}>"
            else:
                recipient = to_email
            
            if not text_body:
                text_body = self._strip_html(html_body)
            
            data = {
                "from": self.sender_email,
                "to": recipient,
                "subject": subject,
                "html": html_body,
                "text": text_body,
            }
            
            if reply_to:
                data["h:Reply-To"] = reply_to
            
            if cc:
                data["cc"] = ", ".join(cc)
            
            if bcc:
                data["bcc"] = ", ".join(bcc)
            
            if tags:
                data["o:tag"] = tags
            
            if tracking:
                data["o:tracking"] = "yes"
                data["o:tracking-clicks"] = "yes"
                data["o:tracking-opens"] = "yes"
            
            response = requests.post(
                self.api_url,
                auth=self.auth,
                data=data,
                timeout=10
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"❌ Mailgun API error: {response.status_code}")
                logger.error(f"Response: {response.text}")
                raise Exception(f"Mailgun API returned {response.status_code}: {response.text}")
            
            result = response.json()
            message_id = result.get("id", "unknown")
            
            logger.info(f"Email sent to {to_email}")
            logger.info(f"Message ID: {message_id}")
            logger.info(f"Status: {result.get('message', 'Queued')}")
            
            return {
                "success": True,
                "message_id": message_id,
                "to_email": to_email,
                "to_name": to_name,
                "subject": subject,
                "status": "sent",
                "timestamp": result.get("timestamp"),
            }
        
        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout sending email to {to_email}")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Connection error sending email to {to_email}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
            raise
     
    @staticmethod
    def _strip_html(html_text: str) -> str:
        """Convert HTML to plain text by removing all tags"""
        return re.sub('<[^<]+?>', '', html_text)


# Initialize service singleton
try:
    mailgun_service = MailgunService()
except Exception as e:
    logger.error(f"Failed to initialize Mailgun service: {str(e)}")
    mailgun_service = None