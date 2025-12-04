"""Campaign Email API Routes"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
from services.campaign_email_service import CampaignEmailService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/campaign-emails", tags=["campaign-emails"])

campaign_email_service = CampaignEmailService()


# Request Models
class GenerateMonth1EmailsRequest(BaseModel):
    campaign_id: str
    campaign_name: str
    persona: str
    objective: str
    target_city: Optional[str] = "your market"


class EmailContent(BaseModel):
    category_id: str
    category_name: str
    subject: str
    body: str
    send_day: int
    order: int
    month_phase: str
    month_number: int


class SaveApprovedEmailsRequest(BaseModel):
    campaign_id: str
    user_id: str
    emails: List[EmailContent]
    campaign_start_date: Optional[str] = None  # ISO format


class UpdateEmailRequest(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None


class RegenerateEmailRequest(BaseModel):
    campaign_name: str
    persona: str
    objective: str
    target_city: List[str]


@router.post("/generate-month-1")
async def generate_month_1_emails(request: GenerateMonth1EmailsRequest):
    """
    Generate 5 Month 1 emails using AI
    Returns draft emails for user review (not saved to DB)
    """
    try:
        emails = campaign_email_service.generate_month_1_emails(
            campaign_id=request.campaign_id,
            campaign_name=request.campaign_name,
            persona=request.persona,
            objective=request.objective,
            target_city=request.target_city,
        )
        
        return {
            "success": True,
            "emails": emails,
            "total": len(emails),
            "phase": "month_1",
        }
    
    except Exception as e:
        logger.error(f"Error generating Month 1 emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-approved")
async def save_approved_emails(request: SaveApprovedEmailsRequest):
    """
    Save user-approved emails to database with scheduled send dates
    Called after user reviews and approves the generated emails
    """
    try:
        # Parse campaign start date if provided
        campaign_start_date = None
        if request.campaign_start_date:
            campaign_start_date = datetime.fromisoformat(request.campaign_start_date.replace('Z', '+00:00'))
        
        # Convert Pydantic models to dicts
        emails_dict = [email.dict() for email in request.emails]
        
        result = campaign_email_service.save_approved_emails(
            campaign_id=request.campaign_id,
            user_id=request.user_id,
            emails=emails_dict,
            campaign_start_date=campaign_start_date,
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error saving approved emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaign/{campaign_id}")
async def get_campaign_emails(campaign_id: str):
    """
    Get all emails for a campaign
    """
    try:
        emails = campaign_email_service.get_campaign_emails(campaign_id)
        
        return {
            "success": True,
            "campaign_id": campaign_id,
            "emails": emails,
            "total": len(emails),
        }
    
    except Exception as e:
        logger.error(f"Error fetching campaign emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/email/{email_id}")
async def update_email(email_id: str, request: UpdateEmailRequest):
    """
    Update an email's subject or body
    Used when user edits a draft email
    """
    try:
        result = campaign_email_service.update_email(
            email_id=email_id,
            subject=request.subject,
            body=request.body,
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error updating email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/email/{email_id}/regenerate")
async def regenerate_email(email_id: str, request: RegenerateEmailRequest):
    """
    Regenerate a single email using AI
    Used when user wants a fresh version of an email
    """
    try:
        result = campaign_email_service.regenerate_email(
            email_id=email_id,
            campaign_name=request.campaign_name,
            persona=request.persona,
            objective=request.objective,
            target_city=request.target_city,
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error regenerating email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/email/{email_id}")
async def delete_email(email_id: str):
    """
    Delete a campaign email
    """
    try:
        from services.supabase_service import get_supabase_client
        supabase = get_supabase_client()
        
        response = supabase.table('campaign_emails').delete().eq('id', email_id).execute()
        
        return {
            "success": True,
            "email_id": email_id,
            "deleted": True,
        }
    
    except Exception as e:
        logger.error(f"Error deleting email: {e}")
        raise HTTPException(status_code=500, detail=str(e))
