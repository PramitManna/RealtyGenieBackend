"""Batches management routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
from services.supabase_service import get_supabase_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/batches", tags=["batches"])

# Models
class BatchUpdateRequest(BaseModel):
    name: Optional[str] = None
    objective: Optional[str] = None
    tone_override: Optional[List[str]] = None
    schedule_cadence: Optional[str] = None

class UserTonesResponse(BaseModel):
    tones: List[str]


@router.put("/{batch_id}")
async def update_batch(
    batch_id: str,
    user_id: str,
    update_data: BatchUpdateRequest
):
    """
    Update batch metadata (name, objective, tone_override, schedule_cadence)
    """
    try:
        # Build updates dictionary with only provided fields
        updates = {}
        if update_data.name is not None:
            updates['name'] = update_data.name
        if update_data.objective is not None:
            updates['objective'] = update_data.objective
        if update_data.tone_override is not None:
            updates['tone_override'] = update_data.tone_override
        if update_data.schedule_cadence is not None:
            updates['schedule_cadence'] = update_data.schedule_cadence
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        supabase = get_supabase_service()
        result = supabase.update_batch(batch_id, user_id, updates)
        
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


@router.get("/user-tones/{user_id}", response_model=UserTonesResponse)
async def get_user_tones(user_id: str):
    """
    Get user's communication tones from profile
    """
    try:
        supabase = get_supabase_service()
        response = supabase.client.table('profiles').select('tones').eq('id', user_id).execute()
        
        if not response.data:
            logger.warning(f"User {user_id} not found")
            return UserTonesResponse(tones=[])
        
        user_tones = response.data[0].get('tones', [])
        # Ensure it's a list
        if isinstance(user_tones, str):
            user_tones = [user_tones]
        
        logger.info(f"Retrieved {len(user_tones)} tones for user {user_id}")
        return UserTonesResponse(tones=user_tones or [])
    
    except Exception as e:
        logger.error(f"Error fetching user tones: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
