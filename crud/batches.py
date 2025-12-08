"""CRUD operations for batches"""
import logging
from typing import Optional, Dict
from supabase import Client

logger = logging.getLogger(__name__)


def update_batch(client: Client, batch_id: str, user_id: str, updates: dict) -> dict:
    """
    Update batch metadata
    
    Args:
        client: Supabase client
        batch_id: ID of batch to update
        user_id: User ID (for authorization)
        updates: Dictionary of fields to update (batch_name, objective, tone_override, 
                 schedule_cadence, subject, body, email_template, description, persona, status, etc.)
    
    Returns:
        Dict with success status, batch_id, and updated data
    """
    try:
        # First verify user owns this batch
        response = client.table('batches').select('id').eq('id', batch_id).eq('user_id', user_id).execute()
        
        if not response.data:
            logger.error(f"Batch {batch_id} not found or does not belong to user {user_id}")
            raise ValueError("Batch not found or access denied")
        
        # Update the batch
        update_response = client.table('batches').update(updates).eq('id', batch_id).execute()
        
        if update_response.data:
            logger.info(f"Updated batch {batch_id}")
            return {
                "success": True,
                "batch_id": batch_id,
                "data": update_response.data[0]
            }
        else:
            raise Exception("No data returned from update")
    
    except Exception as e:
        logger.error(f"Error updating batch {batch_id}: {e}")
        raise
