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
    
    # def send_batch_emails(
    #     self,
    #     recipients: List[Dict],
    #     subject: str,
    #     html_body: str,
    #     text_body: Optional[str] = None,
    #     reply_to: Optional[str] = None,
    #     tags: Optional[List[str]] = None,
    # ) -> Dict:
    #     """
    #     Send emails to multiple recipients
        
    #     Args:
    #         recipients: List of dicts with 'email' and 'name' keys
    #         subject: Email subject
    #         html_body: Email body in HTML format
    #         text_body: Email body in plain text (optional)
    #         reply_to: Reply-to email address (optional)
    #         tags: List of tags for tracking (optional)
        
    #     Returns:
    #         Summary dict with success/failed counts and details
    #     """
    #     results = {
    #         "total": len(recipients),
    #         "sent": 0,
    #         "failed": 0,
    #         "message_ids": [],
    #         "errors": []
    #     }
        
    #     for recipient in recipients:
    #         try:
    #             email = recipient.get("email")
    #             name = recipient.get("name")
                
    #             if not email:
    #                 results["failed"] += 1
    #                 results["errors"].append({
    #                     "email": "unknown",
    #                     "error": "Missing email address"
    #                 })
    #                 continue
                
    #             response = self.send_email(
    #                 to_email=email,
    #                 to_name=name,
    #                 subject=subject,
    #                 html_body=html_body,
    #                 text_body=text_body,
    #                 reply_to=reply_to,
    #                 tags=tags,
    #             )
                
    #             results["sent"] += 1
    #             results["message_ids"].append(response["message_id"])
            
    #         except Exception as e:
    #             results["failed"] += 1
    #             results["errors"].append({
    #                 "email": email,
    #                 "error": str(e)
    #             })
    #             logger.warning(f"Failed to send to {email}: {str(e)}")
        
    #     logger.info(f"📊 Batch send complete: {results['sent']}/{results['total']} successful")
    #     return results
    
    # def send_templated_email(
    #     self,
    #     to_email: str,
    #     to_name: Optional[str] = None,
    #     template_name: str = "",
    #     template_variables: Optional[Dict] = None,
    #     subject: str = "",
    #     reply_to: Optional[str] = None,
    #     tags: Optional[List[str]] = None,
    # ) -> Dict:
    #     """
    #     Send email using Mailgun template
        
    #     Args:
    #         to_email: Recipient email address
    #         to_name: Recipient name (optional)
    #         template_name: Name of Mailgun template to use
    #         template_variables: Variables to substitute in template
    #         subject: Email subject (overrides template subject if provided)
    #         reply_to: Reply-to email address (optional)
    #         tags: List of tags for tracking (optional)
        
    #     Returns:
    #         Response dict with message_id and status
    #     """
    #     try:
    #         if to_name:
    #             recipient = f"{to_name} <{to_email}>"
    #         else:
    #             recipient = to_email
            
    #         # Prepare template data
    #         data = {
    #             "from": self.sender_email,
    #             "to": recipient,
    #             "template": template_name,
    #         }
            
    #         # Add template variables
    #         if template_variables:
    #             for key, value in template_variables.items():
    #                 data[f"v:{key}"] = value
            
    #         if subject:
    #             data["subject"] = subject
            
    #         if reply_to:
    #             data["h:Reply-To"] = reply_to
            
    #         if tags:
    #             data["o:tag"] = tags
            
    #         # Send via Mailgun
    #         response = requests.post(
    #             self.api_url,
    #             auth=self.auth,
    #             data=data,
    #             timeout=10
    #         )
            
    #         if response.status_code not in [200, 201]:
    #             raise Exception(f"Mailgun API returned {response.status_code}: {response.text}")
            
    #         result = response.json()
    #         message_id = result.get("id", "unknown")
            
    #         logger.info(f"✅ Templated email sent to {to_email}")
    #         logger.info(f"📧 Template: {template_name} | Message ID: {message_id}")
            
    #         return {
    #             "success": True,
    #             "message_id": message_id,
    #             "to_email": to_email,
    #             "template": template_name,
    #             "status": "sent",
    #         }
        
    #     except Exception as e:
    #         logger.error(f"❌ Failed to send templated email to {to_email}: {str(e)}")
    #         raise
    
    # def get_email_stats(self, start_date: str = "", end_date: str = "") -> Dict:
    #     """
    #     Get email statistics for the domain
        
    #     Args:
    #         start_date: Start date for stats (optional, format: YYYY-MM-DD)
    #         end_date: End date for stats (optional, format: YYYY-MM-DD)
        
    #     Returns:
    #         Stats dict with sent, delivered, bounced, etc.
    #     """
    #     try:
    #         stats_url = f"https://api.mailgun.net/v3/{self.domain}/stats/total"
            
    #         params = {}
    #         if start_date:
    #             params["start"] = start_date
    #         if end_date:
    #             params["end"] = end_date
            
    #         response = requests.get(
    #             stats_url,
    #             auth=self.auth,
    #             params=params,
    #             timeout=10
    #         )
            
    #         if response.status_code != 200:
    #             raise Exception(f"Failed to fetch stats: {response.text}")
            
    #         return response.json()
        
    #     except Exception as e:
    #         logger.error(f"❌ Failed to fetch email stats: {str(e)}")
    #         raise
    
    # def validate_email(self, email: str) -> Dict:
    #     """
    #     Validate an email address using Mailgun validation API
        
    #     Args:
    #         email: Email address to validate
        
    #     Returns:
    #         Validation result dict
    #     """
    #     try:
    #         validate_url = "https://api.mailgun.net/v4/address/validate"
            
    #         response = requests.get(
    #             validate_url,
    #             auth=("api", self.api_key),
    #             params={"address": email},
    #             timeout=10
    #         )
            
    #         if response.status_code != 200:
    #             raise Exception(f"Validation failed: {response.text}")
            
    #         result = response.json()
            
    #         logger.info(f"📧 Email validation for {email}: {result.get('result', 'unknown')}")
            
    #         return result
        
    #     except Exception as e:
    #         logger.error(f"❌ Failed to validate email {email}: {str(e)}")
    #         raise
    
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