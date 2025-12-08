"""
Cron Job Handler for Campaign Email Sending
Processes pending emails from the queue and handles sending via Mailgun
To be run hourly via a scheduled task or cron service
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import json

from services.supabase_service import get_supabase_client
from services.mailgun_service import mailgun_service
from utils.timezone_service import is_within_send_window

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def replace_email_placeholders(
    text: str,
    recipient_name: str = "Recipient",
    city: str = "your city",
    agent_name: str = "Your Agent",
    company: str = "Your Company",
) -> str:
    """
    Replace email placeholders with actual values.
    
    Args:
        text: Email content with placeholders
        recipient_name: Lead's name
        city: Target city
        agent_name: Agent's name
        company: Company/brokerage name
    
    Returns:
        Text with all placeholders replaced
    """
    year = str(datetime.now().year)
    
    replacements = {
        '{{recipient_name}}': recipient_name,
        '{{city}}': city,
        '{{agent_name}}': agent_name,
        '{{company}}': company,
        '{{year}}': year,
    }
    
    result = text
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    
    return result


async def send_pending_emails(dry_run: bool = False) -> Dict:
    """
    Process and send all pending emails scheduled for the current time.
    Works with the new campaign_emails system.
    
    Args:
        dry_run: If True, don't actually send emails, just log what would be sent
    
    Returns:
        Statistics dict with sent/failed counts
    """
    stats = {
        "processed": 0,
        "sent": 0,
        "failed": 0,
        "skipped": 0,
        "errors": [],
    }
    
    try:
        supabase = get_supabase_client()
        
        # Get all pending emails scheduled for now or earlier
        now = datetime.utcnow().isoformat()
        pending_response = supabase.table("campaign_send_queue").select("*").eq("status", "pending").lte("scheduled_for", now).order("scheduled_for", desc=False).limit(100).execute()
        
        pending_emails = pending_response.data if pending_response.data else []
        
        logger.info(f"🚀 Processing {len(pending_emails)} pending emails")
        
        for email_queue in pending_emails:
            stats["processed"] += 1
            queue_id = email_queue["id"]
            
            try:
                # Check if it's time to send
                scheduled_time = datetime.fromisoformat(email_queue["scheduled_for"].replace("Z", "+00:00"))
                if scheduled_time > datetime.utcnow():
                    stats["skipped"] += 1
                    continue
                
                # Get the email for this send_day from campaign_emails
                email_response = supabase.table("campaign_emails").select("subject, body, user_id").eq("campaign_id", email_queue["campaign_id"]).eq("send_day", email_queue.get("send_day", 0)).limit(1).execute()
                
                if not email_response.data:
                    logger.error(f"❌ Email not found for campaign {email_queue['campaign_id']}, send_day {email_queue.get('send_day', 0)}")
                    stats["failed"] += 1
                    continue
                
                email_data = email_response.data[0]
                
                # Get agent info from user profile
                agent_name = "Your Agent"
                company_name = "Your Company"
                city = "your city"
                
                try:
                    user_id = email_data.get('user_id')
                    if user_id:
                        profile_response = supabase.table('profiles').select('full_name, company_name, markets').eq('id', user_id).single().execute()
                        if profile_response.data:
                            agent_name = profile_response.data.get('full_name', agent_name)
                            company_name = profile_response.data.get('brokerage', company_name)
                            markets = profile_response.data.get('markets', [])
                            if markets and len(markets) > 0:
                                city = markets[0]
                except Exception as e:
                    logger.warning(f"Could not fetch profile: {e}")
                
                recipient_name = email_queue.get('recipient_name', 'Recipient')
                
                # Replace placeholders
                personalized_subject = replace_email_placeholders(
                    email_data['subject'],
                    recipient_name=recipient_name,
                    city=city,
                    agent_name=agent_name,
                    company=company_name,
                )
                
                personalized_body = replace_email_placeholders(
                    email_data['body'],
                    recipient_name=recipient_name,
                    city=city,
                    agent_name=agent_name,
                    company=company_name,
                )
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would send to {email_queue['recipient_email']}")
                    stats["sent"] += 1
                    continue
                
                # Send via Mailgun
                if not mailgun_service:
                    raise Exception("Mailgun service not initialized")
                
                logger.info(f"📧 Sending Day {email_queue.get('send_day', 0)} to {email_queue['recipient_email']}")
                
                result = mailgun_service.send_email(
                    to_email=email_queue['recipient_email'],
                    to_name=recipient_name,
                    subject=personalized_subject,
                    html_body=personalized_body,
                    tags=[f"day_{email_queue.get('send_day', 0)}", 'campaign'],
                )
                
                # Update queue status to sent
                supabase.table("campaign_send_queue").update({
                    "status": "sent",
                    "sent_at": datetime.utcnow().isoformat(),
                }).eq("id", queue_id).execute()
                
                logger.info(f"✅ Sent to {email_queue['recipient_email']}")
                stats["sent"] += 1
                
            except Exception as e:
                error_msg = f"Queue {queue_id}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                stats["failed"] += 1
                stats["errors"].append(error_msg)
                
                # Mark as failed
                try:
                    supabase.table("campaign_send_queue").update({
                        "status": "failed",
                        "error_message": str(e)[:255],
                    }).eq("id", queue_id).execute()
                except Exception as mark_error:
                    logger.error(f"Failed to mark as failed: {str(mark_error)}")
        
        logger.info(f"📊 Cron complete: {stats['sent']}/{stats['processed']} sent")
        return stats
    
    except Exception as e:
        error_msg = f"Cron job failed: {str(e)}"
        logger.error(f"❌ {error_msg}")
        stats["errors"].append(error_msg)
        return stats


async def cleanup_old_queue_entries(days_old: int = 90) -> int:
    """
    Clean up old queue entries that have been sent or failed.
    Keeps records for 90 days for reporting/analytics purposes.
    
    Args:
        days_old: Number of days to keep (default 90)
    
    Returns:
        Number of entries deleted
    """
    supabase = get_supabase_client()
    
    cutoff_date = (datetime.utcnow() - timedelta(days=days_old)).isoformat()
    
    try:
        # Delete old sent emails
        delete_response = supabase.table("campaign_send_queue").delete().eq("status", "sent").lt("updated_at", cutoff_date).execute()
        
        # Delete old failed emails (after max retries exceeded)
        fail_delete = supabase.table("campaign_send_queue").delete().eq("status", "failed").gte("retry_count", 3).lt("updated_at", cutoff_date).execute()
        
        return 0  # Return count if available from Supabase
    
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        return 0


# Health check endpoint data
def get_queue_health() -> Dict:
    """
    Get health status of the email queue.
    Useful for monitoring and alerting.
    
    Returns:
        Health status dict
    """
    supabase = get_supabase_client()
    
    try:
        # Get queue stats
        queue_response = supabase.table("campaign_send_queue").select("status, send_day", count="exact").execute()
        total_count = queue_response.count
        
        pending_response = supabase.table("campaign_send_queue").select("id", count="exact").eq("status", "pending").execute()
        pending_count = pending_response.count
        
        # Get pending emails that are overdue (should have been sent by now)
        overdue_response = supabase.table("campaign_send_queue").select("id", count="exact").eq("status", "pending").lt("scheduled_for", datetime.utcnow().isoformat()).execute()
        overdue_count = overdue_response.count
        
        return {
            "status": "healthy" if overdue_count < 10 else "warning" if overdue_count < 100 else "critical",
            "total_queue_entries": total_count,
            "pending_count": pending_count,
            "overdue_count": overdue_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
