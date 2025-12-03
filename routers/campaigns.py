from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
import uuid
import logging

from services.campaign_queue_service import (
    populate_campaign_queue,
    get_queue_stats,
    cancel_campaign_queue,
    retry_failed_sends,
)
from services.cron_service import send_pending_emails
from utils.timezone_service import get_recipient_timezone, calculate_campaign_queue_times
from services.supabase_service import get_supabase_client

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])
logger = logging.getLogger(__name__)


class CampaignCreateRequest(BaseModel):
    batch_id: str
    subject: str
    body: str
    tones: List[str]
    objective: str
    recipient_timezone: Optional[str] = "America/Toronto"


class CampaignResponse(BaseModel):
    id: str
    batch_id: str
    subject: str
    body: str
    objective: str
    tones: List[str]
    recipient_timezone: str
    status: str
    created_at: str
    queue_stats: Optional[Dict]


class QueueStatsResponse(BaseModel):
    campaign_id: str
    total: int
    pending: int
    sent: int
    failed: int
    by_day: Dict[str, Dict]
    pending_emails: Optional[List[Dict]] = []


@router.post("/create", response_model=CampaignResponse)
async def create_campaign(request: CampaignCreateRequest):
    try:
        supabase = get_supabase_client()
        
        batch_response = supabase.table("batches").select("id, name").eq("id", request.batch_id).single().execute()
        if not batch_response.data:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        leads_response = supabase.table("leads").select("id").eq("batch_id", request.batch_id).eq("status", "active").execute()
        if not leads_response.data:
            raise HTTPException(status_code=400, detail="Batch has no active leads")
        
        campaign_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        campaign_data = {
            "id": campaign_id,
            "batch_id": request.batch_id,
            "subject": request.subject,
            "body": request.body,
            "tones": request.tones,
            "objective": request.objective,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        
        campaign_response = supabase.table("campaigns").insert(campaign_data).execute()
        if not campaign_response.data:
            raise HTTPException(status_code=500, detail="Failed to create campaign")
        
        queue_result = populate_campaign_queue(
            campaign_id=campaign_id,
            batch_id=request.batch_id,
            campaign_created_at=datetime.fromisoformat(now),
            recipient_timezone=request.recipient_timezone,
        )
        
        queue_stats = get_queue_stats(campaign_id)
        
        return CampaignResponse(
            id=campaign_id,
            batch_id=request.batch_id,
            subject=request.subject,
            body=request.body,
            tones=request.tones,
            objective=request.objective,
            status="active",
            created_at=now,
            queue_stats=queue_stats,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create campaign: {str(e)}")


@router.get("/queue-stats/{campaign_id}")
async def get_campaign_queue_stats(campaign_id: str):
    try:
        supabase = get_supabase_client()
        
        campaign_response = supabase.table("campaigns").select("id, user_id").eq("id", campaign_id).single().execute()
        if not campaign_response.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        user_id = campaign_response.data.get('user_id')
        cities = ["your city"]
        if user_id:
            profile_response = supabase.table("profiles").select("markets").eq("id", user_id).single().execute()
            if profile_response.data and profile_response.data.get('markets'):
                cities = profile_response.data['markets']
        
        city_name = cities[0] if cities else "your city"
        
        queue_response = supabase.table("campaign_send_queue").select(
            "send_day, scheduled_for"
        ).eq("campaign_id", campaign_id).eq("status", "pending").order("scheduled_for").execute()
        
        emails_response = supabase.table("campaign_emails").select(
            "subject, send_day"
        ).eq("campaign_id", campaign_id).execute()
        
        emails_by_day = {}
        for email in (emails_response.data or []):
            subject = email['subject']
            subject = subject.replace('{{city}}', city_name)
            subject = subject.replace('{city}', city_name)
            emails_by_day[email['send_day']] = subject
        
        emails_dict = {}
        for entry in (queue_response.data or []):
            send_day = entry.get('send_day')
            if send_day is not None and send_day in emails_by_day:
                if send_day not in emails_dict:
                    emails_dict[send_day] = {
                        'subject': emails_by_day[send_day],
                        'send_day': send_day,
                        'scheduled_for': entry.get('scheduled_for'),
                        'pending_count': 0
                    }
                emails_dict[send_day]['pending_count'] += 1
        
        pending_emails = sorted(emails_dict.values(), key=lambda x: x['send_day'])
        
        return {
            "campaign_id": campaign_id,
            "pending_emails": pending_emails
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch pending emails: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch pending emails: {str(e)}")


@router.post("/pause/{campaign_id}")
async def pause_campaign(campaign_id: str):
    try:
        supabase = get_supabase_client()
        
        campaign_response = supabase.table("campaigns").select("id").eq("id", campaign_id).single().execute()
        if not campaign_response.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        update_response = supabase.table("campaigns").update({
            "status": "paused",
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", campaign_id).execute()
        
        return {
            "message": "Campaign paused successfully",
            "campaign_id": campaign_id,
            "status": "paused",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pause campaign: {str(e)}")


@router.post("/resume/{campaign_id}")
async def resume_campaign(campaign_id: str):
    try:
        supabase = get_supabase_client()
        
        campaign_response = supabase.table("campaigns").select("id").eq("id", campaign_id).single().execute()
        if not campaign_response.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        update_response = supabase.table("campaigns").update({
            "status": "active",
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", campaign_id).execute()
        
        return {
            "message": "Campaign resumed successfully",
            "campaign_id": campaign_id,
            "status": "active",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume campaign: {str(e)}")


@router.post("/cancel/{campaign_id}")
async def cancel_campaign(campaign_id: str):
    try:
        supabase = get_supabase_client()
        
        campaign_response = supabase.table("campaigns").select("id").eq("id", campaign_id).single().execute()
        if not campaign_response.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        canceled_count = cancel_campaign_queue(campaign_id)
        
        supabase.table("campaigns").update({
            "status": "canceled",
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", campaign_id).execute()
        
        return {
            "message": "Campaign canceled successfully",
            "campaign_id": campaign_id,
            "status": "canceled",
            "queue_entries_canceled": canceled_count,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel campaign: {str(e)}")


@router.post("/retry-failed/{campaign_id}")
async def retry_failed_campaign_sends(campaign_id: str, max_retries: int = 3):
    """
    Retry failed sends for a campaign.
    
    Args:
        campaign_id: UUID of the campaign
        max_retries: Maximum retry attempts (default 3)
    
    Returns:
        Number of entries reset for retry
    
    Raises:
        HTTPException: If campaign not found
    """
    try:
        supabase = get_supabase_client()
        
        campaign_response = supabase.table("campaigns").select("id").eq("id", campaign_id).single().execute()
        if not campaign_response.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        retry_count = retry_failed_sends(campaign_id, max_retries)
        
        return {
            "message": "Failed sends queued for retry",
            "campaign_id": campaign_id,
            "retried_count": retry_count,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retry sends: {str(e)}")


@router.get("/send-schedule/{campaign_id}/{lead_id}")
async def get_campaign_send_schedule(campaign_id: str, lead_id: str):
    """
    Get the send schedule for a specific lead in a campaign (all D0, D10, D20, D30 times).
    
    Args:
        campaign_id: UUID of the campaign
        lead_id: UUID of the lead
    
    Returns:
        Send times for each day with local timezone conversions
    
    Raises:
        HTTPException: If campaign or lead not found
    """
    try:
        supabase = get_supabase_client()
        
        campaign_response = supabase.table("campaigns").select("created_at, recipient_timezone").eq("id", campaign_id).single().execute()
        if not campaign_response.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        lead_response = supabase.table("leads").select("timezone, city").eq("id", lead_id).single().execute()
        if not lead_response.data:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        campaign = campaign_response.data
        lead = lead_response.data
        
        timezone = lead.get("timezone") or campaign.get("recipient_timezone", "America/Toronto")
        
        campaign_created = datetime.fromisoformat(campaign["created_at"].replace("Z", "+00:00"))
        schedule = calculate_campaign_queue_times(campaign_created, timezone)
        
        return {
            "campaign_id": campaign_id,
            "lead_id": lead_id,
            "timezone": timezone,
            "schedule": schedule,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch send schedule: {str(e)}")


class GenerateDraftsRequest(BaseModel):
    campaign_id: str
    campaign_name: str
    target_city: List[str]
    tones: List[str]  # All tones to blend
    objective: str
    user_id: str


class EmailDraft(BaseModel):
    category_id: str
    category_name: str
    subject: str
    body: str
    send_day: int
    order: int


class GenerateDraftsResponse(BaseModel):
    success: bool
    campaign_id: str
    emails: List[EmailDraft]
    total: int
    phase: str


@router.post("/generate-drafts", response_model=GenerateDraftsResponse)
async def generate_email_drafts(request: GenerateDraftsRequest):
    """
    Generate Month 1 email drafts using Google Gemini AI.
    
    Args:
        request: Campaign details for draft generation
    
    Returns:
        List of 5 Month 1 email drafts with subject and body (not saved to DB)
    
    Raises:
        HTTPException: If Gemini service unavailable or generation fails
    """
    try:
        from services.campaign_email_service import CampaignEmailService

        print(request.model_dump_json())
        
        supabase = get_supabase_client()
        
        user_agent_name = "Your Name"
        user_company_name = "Your Company"
        target_city = ["your city"]
        
        try:
            profile_response = supabase.table('profiles').select(
                'full_name, brokerage, markets'
            ).eq('id', request.user_id).single().execute()

            
            if profile_response.data:
                user_agent_name = profile_response.data.get('full_name', user_agent_name)
                user_company_name = profile_response.data.get('brokerage', user_company_name)
                target_city=profile_response.get('markets', target_city),
                
        except Exception as e:
            logger.warning(f"Could not fetch user profile: {e}")
        
        campaign_email_service = CampaignEmailService()
        
        emails = campaign_email_service.generate_month_1_emails(
            campaign_id=request.campaign_id,
            campaign_name=request.campaign_name,
            tones=request.tones,
            objective=request.objective,
            target_city=target_city,
            agent_name=user_agent_name,
            company_name=user_company_name,
        )
        
        return GenerateDraftsResponse(
            success=True,
            campaign_id=request.campaign_id,
            emails=emails,
            total=len(emails),
            phase="month_1"
        )
    
    except Exception as e:
        logger.error(f"Error generating drafts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate drafts: {str(e)}")


@router.get("/pending-queue/{campaign_id}")
async def get_pending_campaign_emails(campaign_id: str):
    """
    Get all pending emails for a campaign from the send queue.
    Shows what emails are scheduled to be sent in the future.
    
    Args:
        campaign_id: UUID of the campaign
    
    Returns:
        List of pending emails with their scheduled send dates
    """
    try:
        logger.info(f"Fetching pending emails for campaign: {campaign_id}")
        supabase = get_supabase_client()
        
        # Verify campaign exists
        campaign_response = supabase.table("campaigns").select("id").eq("id", campaign_id).single().execute()
        if not campaign_response.data:
            logger.warning(f"Campaign not found: {campaign_id}")
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Fetch pending queue entries
        queue_response = supabase.table("campaign_send_queue").select(
            "id, email_id, lead_id, scheduled_for, status, send_day"
        ).eq("campaign_id", campaign_id).eq("status", "pending").order("scheduled_for").execute()
        
        logger.info(f"Found {len(queue_response.data or [])} pending queue entries for campaign {campaign_id}")
        
        # Get unique email IDs to fetch email details
        email_ids = list(set([entry.get('email_id') for entry in (queue_response.data or []) if entry.get('email_id')]))
        
        # Fetch email details
        emails_data = {}
        if email_ids:
            emails_response = supabase.table("campaign_emails").select(
                "id, subject, category_name"
            ).in_("id", email_ids).execute()
            
            for email in (emails_response.data or []):
                emails_data[email['id']] = email
        
        # Group by email (same subject = same email type)
        emails_dict = {}
        for entry in (queue_response.data or []):
            email_id = entry.get('email_id')
            if email_id and email_id in emails_data:
                email_info = emails_data[email_id]
                subject = email_info.get('subject')
                if subject not in emails_dict:
                    emails_dict[subject] = {
                        'subject': subject,
                        'category_name': email_info.get('category_name'),
                        'send_day': entry.get('send_day'),
                        'scheduled_for': entry.get('scheduled_for'),
                        'pending_count': 0
                    }
                emails_dict[subject]['pending_count'] += 1
        
        # Convert to list and sort by scheduled date
        pending_emails = sorted(emails_dict.values(), key=lambda x: x['scheduled_for'] or '')
        
        return {
            "campaign_id": campaign_id,
            "pending_emails": pending_emails,
            "total_pending": len(queue_response.data or [])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch pending emails for {campaign_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch pending emails: {str(e)}")


@router.post("/send-pending")
async def send_pending_emails_endpoint(dry_run: bool = False):
    try:
        stats = await send_pending_emails(dry_run=dry_run)
        return {
            "success": True,
            "dry_run": dry_run,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send pending emails: {str(e)}")