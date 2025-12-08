"""Batches management routes - now handles automation triggers directly"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging
import uuid
from datetime import datetime
from services.supabase_service import get_supabase_service, get_supabase_client
from services.campaign_queue_service import (
    populate_campaign_queue,
    get_queue_stats,
    cancel_campaign_queue,
    retry_failed_sends,
)
import crud.batches as crud_batches

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/batches", tags=["batches"])

# Models
class BatchUpdateRequest(BaseModel):
    name: Optional[str] = None
    objective: Optional[str] = None
    tone_override: Optional[List[str]] = None
    schedule_cadence: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    email_template: Optional[str] = None
    description: Optional[str] = None
    persona: Optional[str] = None
    status: Optional[str] = None

class BatchStartAutomationRequest(BaseModel):
    subject: str
    body: str
    persona: str
    email_template: Optional[str] = None
    recipient_timezone: Optional[str] = "America/Toronto"

class BatchAutomationResponse(BaseModel):
    success: bool
    message: str
    batch_id: str
    total_recipients: int
    queue_stats: Optional[Dict] = None

@router.put("/{batch_id}")
async def update_batch(
    batch_id: str,
    user_id: str,
    update_data: BatchUpdateRequest
):
    """
    Update batch metadata (name, objective, tone_override, schedule_cadence, email content, etc.)
    """
    try:
        # Build updates dictionary with only provided fields
        updates = {}
        if update_data.name is not None:
            updates['batch_name'] = update_data.name  # Note: column is batch_name in DB
        if update_data.objective is not None:
            updates['objective'] = update_data.objective
        if update_data.tone_override is not None:
            updates['tone_override'] = update_data.tone_override
        if update_data.schedule_cadence is not None:
            updates['schedule_cadence'] = update_data.schedule_cadence
        if update_data.subject is not None:
            updates['subject'] = update_data.subject
        if update_data.body is not None:
            updates['body'] = update_data.body
        if update_data.email_template is not None:
            updates['email_template'] = update_data.email_template
        if update_data.description is not None:
            updates['description'] = update_data.description
        if update_data.persona is not None:
            updates['persona'] = update_data.persona
        if update_data.status is not None:
            updates['status'] = update_data.status
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        supabase = get_supabase_service()
        result = crud_batches.update_batch(supabase.client, batch_id, user_id, updates)
        
        logger.info(f"Updated batch {batch_id} for user {user_id}")
        
        return {
            "success": True,
            "message": "Batch updated successfully",
            "batch_id": batch_id,
            "data": result["data"]
        }
    
    except Exception as e:
        logger.error(f"Error updating batch: {e}")
        if "access denied" in str(e).lower() or "not found" in str(e).lower():
            raise HTTPException(status_code=403, detail="Batch not found or access denied")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/{batch_id}/start-automation", response_model=BatchAutomationResponse)
async def start_batch_automation(
    batch_id: str,
    user_id: str,
    request: BatchStartAutomationRequest
):
    """
    Start automation for a batch - replaces campaign creation flow
    Updates batch with email content and triggers automation queue
    """
    try:
        supabase = get_supabase_client()
        
        # Get batch info
        batch_response = supabase.table("batches").select("id, batch_name, user_id, lead_count").eq("id", batch_id).eq("user_id", user_id).single().execute()
        if not batch_response.data:
            raise HTTPException(status_code=404, detail="Batch not found or access denied")
        
        batch_data = batch_response.data
        
        # Get active leads for this batch
        leads_response = supabase.table("leads").select("id").eq("batch_id", batch_id).eq("status", "active").execute()
        if not leads_response.data:
            raise HTTPException(status_code=400, detail="Batch has no active leads")
        
        total_recipients = len(leads_response.data)
        now = datetime.utcnow().isoformat()
        
        # Update batch with automation details
        batch_update = {
            "subject": request.subject,
            "body": request.body,
            "email_template": request.email_template or request.body,
            "persona": request.persona,
            "status": "active",
            "total_recipients": total_recipients,
            "emails_sent": 0,
            "updated_at": now,
        }
        
        update_response = supabase.table("batches").update(batch_update).eq("id", batch_id).execute()
        if not update_response.data:
            raise HTTPException(status_code=500, detail="Failed to update batch")
        
        # Populate automation queue (using batch_id as the identifier)
        queue_result = populate_campaign_queue(
            campaign_id=batch_id,  # Use batch_id instead of campaign_id
            batch_id=batch_id,
            campaign_created_at=datetime.fromisoformat(now),
            recipient_timezone=request.recipient_timezone,
        )
        
        # Get queue stats
        queue_stats = get_queue_stats(batch_id)
        
        logger.info(f"Started automation for batch {batch_id} with {total_recipients} recipients")
        
        return BatchAutomationResponse(
            success=True,
            message="Automation started successfully",
            batch_id=batch_id,
            total_recipients=total_recipients,
            queue_stats=queue_stats,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting batch automation: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/{batch_id}/pause")
async def pause_batch_automation(batch_id: str, user_id: str):
    """
    Pause automation for a batch
    """
    try:
        supabase = get_supabase_client()
        
        # Verify batch ownership
        batch_response = supabase.table("batches").select("id").eq("id", batch_id).eq("user_id", user_id).single().execute()
        if not batch_response.data:
            raise HTTPException(status_code=404, detail="Batch not found or access denied")
        
        # Update status
        update_response = supabase.table("batches").update({"status": "paused"}).eq("id", batch_id).execute()
        
        logger.info(f"Paused automation for batch {batch_id}")
        
        return {"success": True, "message": "Batch automation paused"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing batch: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/{batch_id}/resume")
async def resume_batch_automation(batch_id: str, user_id: str):
    """
    Resume automation for a batch
    """
    try:
        supabase = get_supabase_client()
        
        # Verify batch ownership
        batch_response = supabase.table("batches").select("id").eq("id", batch_id).eq("user_id", user_id).single().execute()
        if not batch_response.data:
            raise HTTPException(status_code=404, detail="Batch not found or access denied")
        
        # Update status
        update_response = supabase.table("batches").update({"status": "active"}).eq("id", batch_id).execute()
        
        logger.info(f"Resumed automation for batch {batch_id}")
        
        return {"success": True, "message": "Batch automation resumed"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming batch: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/{batch_id}/queue-stats")
async def get_batch_queue_stats(batch_id: str, user_id: str):
    """
    Get automation queue statistics for a batch
    """
    try:
        supabase = get_supabase_client()
        
        # Verify batch ownership
        batch_response = supabase.table("batches").select("id").eq("id", batch_id).eq("user_id", user_id).single().execute()
        if not batch_response.data:
            raise HTTPException(status_code=404, detail="Batch not found or access denied")
        
        # Get queue stats
        stats = get_queue_stats(batch_id)
        
        return stats
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching queue stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
