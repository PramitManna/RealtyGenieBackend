"""
Campaign Queue Management Service
Handles scheduling of emails for D0, D10, D20, D30 campaign touches
with timezone-aware send time calculations
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
from enum import Enum

from services.supabase_service import get_supabase_client
from utils.timezone_service import (
    calculate_send_time_in_timezone,
    is_within_send_window,
    get_next_valid_send_time,
    get_recipient_timezone,
)


class SendDay(int, Enum):
    """Campaign email send day offsets"""
    DAY_0 = 0      # Immediate send on campaign creation
    DAY_10 = 10    # 10 days after campaign start
    DAY_20 = 20    # 20 days after campaign start
    DAY_30 = 30    # 30 days after campaign start


class QueueStatus(str, Enum):
    """Status of emails in queue"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"


def populate_campaign_queue(
    campaign_id: str,
    batch_id: str,
    campaign_created_at: datetime,
    recipient_timezone: Optional[str] = "UTC",
    send_window_start: int = 8,
    send_window_end: int = 20,
) -> Dict[str, int]:
    """
    Populate campaign_send_queue for all leads in a batch.
    Creates queue entries for D0, D10, D20, D30 sends with timezone-aware scheduling.
    Ensures all sends occur within recipient's specified send window (default 8am-8pm).
    
    Args:
        campaign_id: UUID of the campaign
        batch_id: UUID of the batch
        campaign_created_at: Campaign creation timestamp
        recipient_timezone: Default timezone for recipients (will be overridden by lead-specific timezone)
        send_window_start: Start of send window in local time (default 8 for 8 AM)
        send_window_end: End of send window in local time (default 20 for 8 PM)
    
    Returns:
        Dict with counts: {
            "total_queued": int,
            "day_0": int,
            "day_10": int,
            "day_20": int,
            "day_30": int
        }
    """
    supabase = get_supabase_client()
    
    # Ensure campaign_created_at is timezone-aware
    if not campaign_created_at.tzinfo:
        import pytz
        campaign_created_at = campaign_created_at.replace(tzinfo=pytz.UTC)
    
    # Fetch all active leads in the batch with timezone info
    leads_response = supabase.table("leads").select("id, email, name, city, timezone").eq("batch_id", batch_id).eq("status", "active").execute()
    leads = leads_response.data if leads_response.data else []
    
    # Fetch campaign details
    campaign_response = supabase.table("campaigns").select("subject, body, recipient_timezone").eq("id", campaign_id).single().execute()
    campaign = campaign_response.data
    
    # Use campaign-specific timezone if available, otherwise use provided timezone
    campaign_timezone = campaign.get("recipient_timezone", recipient_timezone) or "UTC"
    
    queue_entries = []
    send_days_count = {0: 0, 10: 0, 20: 0, 30: 0}
    
    for lead in leads:
        # Determine recipient timezone (lead-specific > campaign > default)
        lead_timezone = lead.get("timezone")
        if not lead_timezone:
            lead_timezone = get_recipient_timezone(lead)
        
        # Create queue entry for each send day
        for send_day in [SendDay.DAY_0, SendDay.DAY_10, SendDay.DAY_20, SendDay.DAY_30]:
            # Calculate base time (UTC): campaign creation + day offset
            base_utc = campaign_created_at + timedelta(days=send_day.value)
            
            # Calculate send time for recipient's local morning (8 AM in their timezone)
            scheduled_utc = calculate_send_time_in_timezone(
                base_utc,
                lead_timezone,
                target_hour=send_window_start,
                target_minute=0,
            )
            
            # Verify it's within send window, if not, move to next valid time
            if not is_within_send_window(scheduled_utc, lead_timezone, send_window_start, send_window_end):
                scheduled_utc = get_next_valid_send_time(
                    scheduled_utc,
                    lead_timezone,
                    send_window_start,
                    send_window_end,
                )
            
            queue_entry = {
                "campaign_id": campaign_id,
                "lead_id": lead["id"],
                "recipient_email": lead["email"],
                "recipient_name": lead.get("name", ""),
                "send_day": send_day.value,
                "scheduled_for": scheduled_utc.isoformat(),
                "recipient_timezone": lead_timezone,
                "recipient_local_send_time": f"{send_window_start:02d}:00:00",  # 8:00 AM in local time
                "status": QueueStatus.PENDING.value,
            }
            queue_entries.append(queue_entry)
            send_days_count[send_day.value] += 1
    
    # Batch insert queue entries
    if queue_entries:
        insert_response = supabase.table("campaign_send_queue").insert(queue_entries).execute()
        if not insert_response.data:
            raise Exception(f"Failed to populate queue for campaign {campaign_id}")
    
    return {
        "total_queued": len(queue_entries),
        "day_0": send_days_count[0],
        "day_10": send_days_count[10],
        "day_20": send_days_count[20],
        "day_30": send_days_count[30],
    }


def get_pending_sends(limit: int = 100) -> List[Dict]:
    """
    Fetch pending emails scheduled for sending (uses pending_sends_view).
    Ordered by scheduled_for time (earliest first).
    
    Args:
        limit: Maximum number of pending sends to fetch
    
    Returns:
        List of pending send dictionaries with full context
    """
    supabase = get_supabase_client()
    
    response = supabase.rpc(
        "get_pending_sends",
        {"limit_count": limit}
    ).execute()
    
    return response.data if response.data else []


def mark_send_complete(
    queue_id: str,
    sent_at: Optional[datetime] = None,
    error_message: Optional[str] = None,
) -> Dict:
    """
    Mark a queue entry as sent or failed.
    
    Args:
        queue_id: UUID of queue entry
        sent_at: Timestamp when email was sent (None if failed)
        error_message: Error message if send failed
    
    Returns:
        Updated queue entry
    """
    supabase = get_supabase_client()
    
    status = QueueStatus.SENT.value if sent_at else QueueStatus.FAILED.value
    
    update_data = {
        "status": status,
        "sent_at": sent_at.isoformat() if sent_at else None,
        "error_message": error_message,
    }
    
    response = supabase.table("campaign_send_queue").update(update_data).eq("id", queue_id).execute()
    
    return response.data[0] if response.data else {}


def get_queue_stats(campaign_id: str) -> Dict:
    """
    Get detailed queue statistics for a campaign including breakdown by send_day and status.
    
    Args:
        campaign_id: UUID of the campaign
    
    Returns:
        Dictionary with queue stats:
        {
            "total": int,
            "pending": int,
            "sent": int,
            "failed": int,
            "by_day": {
                "0": {"total": int, "sent": int, "pending": int, "failed": int},
                "5": {"total": int, "sent": int, "pending": int, "failed": int},
                ...
            }
        }
    """
    supabase = get_supabase_client()
    
    # Get all queue entries for campaign
    response = supabase.table("campaign_send_queue").select("status, send_day").eq("campaign_id", campaign_id).execute()
    entries = response.data if response.data else []
    
    # Calculate summary stats
    stats = {
        "total": len(entries),
        "pending": sum(1 for e in entries if e["status"] == QueueStatus.PENDING.value),
        "sent": sum(1 for e in entries if e["status"] == QueueStatus.SENT.value),
        "failed": sum(1 for e in entries if e["status"] == QueueStatus.FAILED.value),
        "by_day": {}
    }
    
    # Get unique send days and break down by status
    send_days = sorted(set(e.get("send_day", 0) for e in entries))
    
    for day in send_days:
        day_entries = [e for e in entries if e.get("send_day") == day]
        stats["by_day"][str(day)] = {
            "total": len(day_entries),
            "sent": sum(1 for e in day_entries if e["status"] == QueueStatus.SENT.value),
            "pending": sum(1 for e in day_entries if e["status"] == QueueStatus.PENDING.value),
            "failed": sum(1 for e in day_entries if e["status"] == QueueStatus.FAILED.value),
        }
    
    return stats


def retry_failed_sends(campaign_id: str, max_retries: int = 3) -> int:
    """
    Retry failed sends for a campaign (up to max_retries).
    Updates retry_count and resets status to pending.
    
    Args:
        campaign_id: UUID of campaign
        max_retries: Maximum retry attempts
    
    Returns:
        Number of entries reset for retry
    """
    supabase = get_supabase_client()
    
    # Get failed entries with retry_count < max_retries
    response = supabase.table("campaign_send_queue").select("id, retry_count").eq("campaign_id", campaign_id).eq("status", QueueStatus.FAILED.value).lt("retry_count", max_retries).execute()
    
    failed_entries = response.data if response.data else []
    
    retry_count = 0
    for entry in failed_entries:
        supabase.table("campaign_send_queue").update({
            "status": QueueStatus.PENDING.value,
            "retry_count": entry["retry_count"] + 1,
            "error_message": None,
        }).eq("id", entry["id"]).execute()
        retry_count += 1
    
    return retry_count


def cancel_campaign_queue(campaign_id: str) -> int:
    """
    Cancel all pending sends for a campaign.
    Useful when campaign is deleted or paused.
    
    Args:
        campaign_id: UUID of campaign
    
    Returns:
        Number of entries canceled
    """
    supabase = get_supabase_client()
    
    # Get all pending entries for campaign
    response = supabase.table("campaign_send_queue").select("id").eq("campaign_id", campaign_id).eq("status", QueueStatus.PENDING.value).execute()
    
    pending_entries = response.data if response.data else []
    
    # Delete all pending entries
    if pending_entries:
        delete_response = supabase.table("campaign_send_queue").delete().eq("campaign_id", campaign_id).eq("status", QueueStatus.PENDING.value).execute()
    
    return len(pending_entries)
