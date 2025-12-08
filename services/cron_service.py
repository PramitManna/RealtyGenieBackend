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
from services.gemini_service import get_gemini_service
from utils.timezone_service import is_within_send_window

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_premium_festive_email(
    festival_name: str,
    festival_description: str,
    recipient_name: str,
    agent_name: str,
    company_name: str,
    city: str,
    agent_specialty: str = "real estate"
) -> Dict[str, str]:
    """
    Generate a premium, professional festive email using Gemini AI
    
    Args:
        festival_name: Name of the festival (e.g., "Christmas", "Diwali")
        festival_description: Brief context about the festival
        recipient_name: Lead's name
        agent_name: Agent's full name
        company_name: Brokerage/company name
        city: Target city/market
        agent_specialty: Agent's specialty (default: "real estate")
    
    Returns:
        Dict with 'subject' and 'body' keys containing generated content
    """
    try:
        # Initialize Gemini service properly
        from services.gemini_service import GeminiService
        gemini_service = GeminiService()
        gemini_service._ensure_initialized()  # Make sure it's initialized
        
        if not gemini_service or not gemini_service.model:
            logger.warning("Gemini service not available, using fallback template")
            return None
        
        # Premium prompt engineering for high-quality festive emails
        prompt = f"""You are an expert copywriter specializing in luxury real estate communications. 
Your task is to craft an exceptionally warm, professional, and memorable {festival_name} greeting email.

**CONTEXT:**
- Festival: {festival_name} ({festival_description})
- From: {agent_name}, a premium real estate professional at {company_name}
- To: {recipient_name}, a valued client/lead in {city}
- Tone: Warm, genuine, elegant, and relationship-focused (NOT salesy)
- Brand: Sophisticated, trustworthy, community-oriented

**WRITING GUIDELINES:**
1. **Subject Line:** Create a captivating, emoji-enhanced subject (35-50 chars) that feels personal and festive
2. **Opening:** Start with genuine warmth that immediately connects emotionally
3. **Body Structure:**
   - Personal greeting acknowledging the recipient by name
   - Heartfelt festival wishes that feel authentic, not generic
   - Subtle connection to {city} community or local festivities
   - Brief mention of gratitude for the relationship (1 sentence max)
   - Forward-looking statement about the coming year
   - Warm, sincere closing
4. **Tone Balance:** 85% personal warmth, 10% community connection, 5% subtle professionalism
5. **Length:** Keep it concise (150-200 words) - quality over quantity
6. **Avoid:** Hard sells, property mentions, service pitches, corporate jargon, excessive formality
7. **Include:** Genuine emotion, local flavor, cultural sensitivity, memorable closing

**STYLE NOTES:**
- Use short, impactful sentences mixed with flowing prose
- Include 1-2 relevant emojis naturally (not forced)
- Write as if sending to a friend you respect
- Make it feel handwritten, not templated
- Reference the season/festival authentically
- End with something that makes them smile

**OUTPUT FORMAT (JSON):**
{{
  "subject": "your subject line here",
  "body": "your email body here (use \\n for line breaks, keep HTML-free)"
}}

Generate a {festival_name} email that {recipient_name} will actually enjoy reading and remember."""

        # Generate using Gemini
        response = gemini_service.model.generate_content(prompt)
        
        if not response or not response.text:
            logger.warning("Empty response from Gemini")
            return None
        
        # Parse JSON response
        import json
        import re
        
        # Extract JSON from response (handle markdown code blocks)
        text = response.text.strip()
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            result = json.loads(json_match.group())
            logger.info(f"✨ Generated premium {festival_name} email via Gemini AI")
            return result
        else:
            logger.warning("Could not parse JSON from Gemini response")
            return None
            
    except Exception as e:
        logger.error(f"Error generating festive email with Gemini: {e}")
        return None


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


# Festive email configuration with dates
FESTIVE_OCCASIONS = {
    "christmas": {
        "name": "Christmas",
        "month": 12,
        "day": 25,
        "description": "A joyful holiday celebrating love, family, and the spirit of giving",
        "subject": "🎄 Warm Holiday Wishes from {{agent_name}}",
        "template": """
Dear {{recipient_name}},

Wishing you and your loved ones a wonderful Christmas filled with joy, warmth, and cherished moments!

As we celebrate this special season, I want to take a moment to thank you for being part of our real estate community in {{city}}. Your trust and support mean the world to us.

May the new year bring you prosperity, happiness, and perhaps the perfect home you've been dreaming of!

Warmest holiday wishes,
{{agent_name}}
{{company}}
"""
    },
    "new_year": {
        "name": "New Year",
        "month": 1,
        "day": 1,
        "description": "Fresh beginnings and new opportunities as we welcome a brand new year",
        "subject": "🎉 Happy New Year from {{agent_name}}!",
        "template": """
Happy New Year, {{recipient_name}}!

As we step into {{year}}, I want to wish you a year filled with success, new opportunities, and wonderful memories!

Whether you're planning to buy, sell, or invest in {{city}} real estate this year, I'm here to help make your dreams a reality.

Here's to an amazing {{year}} ahead!

Best wishes,
{{agent_name}}
{{company}}
"""
    },
    "canada_day": {
        "name": "Canada Day",
        "month": 7,
        "day": 1,
        "description": "Celebrating Canadian pride, diversity, and our beautiful communities from coast to coast",
        "subject": "🇨🇦 Happy Canada Day from {{agent_name}}!",
        "template": """
Happy Canada Day, {{recipient_name}}!

On this special day, let's celebrate the beautiful country we call home. From coast to coast, Canada offers incredible communities and opportunities - especially right here in {{city}}!

I hope you enjoy the celebrations and create wonderful memories with family and friends.

Proud to serve our community,
{{agent_name}}
{{company}}
"""
    },
    "thanksgiving": {
        "name": "Thanksgiving",
        "month": 10,
        "day": 14,  # 2nd Monday in October (approximate)
        "description": "A time to express gratitude for blessings, community, and meaningful relationships",
        "subject": "🦃 Happy Thanksgiving from {{agent_name}}",
        "template": """
Happy Thanksgiving, {{recipient_name}}!

On this day of gratitude, I want to express my sincere thanks for your trust and support. It's clients and community members like you who make my work in {{city}} real estate so rewarding.

May your Thanksgiving be filled with warmth, delicious food, and quality time with loved ones.

With gratitude,
{{agent_name}}
{{company}}
"""
    },
    "valentines": {
        "name": "Valentine's Day",
        "month": 2,
        "day": 14,
        "description": "Celebrating love, appreciation, and meaningful connections in our lives",
        "subject": "💝 Sending Love and Appreciation - {{agent_name}}",
        "template": """
Happy Valentine's Day, {{recipient_name}}!

Today is all about love and appreciation, and I wanted to let you know how much I value our connection. Whether you're celebrating with a partner, family, or friends, I hope your day is filled with joy!

And if you're in love with the idea of a new home in {{city}}, I'm always here to help! 🏡

Warm wishes,
{{agent_name}}
{{company}}
"""
    },
    "halloween": {
        "name": "Halloween",
        "month": 10,
        "day": 31,
        "description": "A fun celebration of creativity, community spirit, and making memories",
        "subject": "🎃 Have a Spooktacular Halloween! - {{agent_name}}",
        "template": """
Happy Halloween, {{recipient_name}}!

Hope you have a spooktacular day filled with treats (not tricks!) and fun memories.

If you're thinking about a move that's NOT scary, I'm here to make your {{city}} real estate journey smooth and stress-free! 👻🏡

Stay safe and enjoy the festivities!

{{agent_name}}
{{company}}
"""
    }
}


async def send_festive_emails(test_month: int = None, test_day: int = None) -> Dict:
    """
    Check if today matches any festive occasions and send emails to users
    who have enabled that festive occasion.
    
    This should be run daily (ideally at 9 AM local time).
    
    Args:
        test_month: Optional month for testing (1-12)
        test_day: Optional day for testing (1-31)
    
    Returns:
        Statistics dict with sent/failed counts
    """
    stats = {
        "checked_festivals": [],
        "emails_sent": 0,
        "emails_failed": 0,
        "errors": [],
    }
    
    try:
        supabase = get_supabase_client()
        now = datetime.now()
        
        # Use test date if provided, otherwise use current date
        current_month = test_month if test_month else now.month
        current_day = test_day if test_day else now.day
        
        if test_month and test_day:
            logger.info(f"🧪 Testing mode: Using date {current_month}/{current_day} instead of {now.month}/{now.day}")
        
        # Find matching festivals
        matching_festivals = []
        for fest_id, fest_data in FESTIVE_OCCASIONS.items():
            if fest_data["month"] == current_month and fest_data["day"] == current_day:
                matching_festivals.append((fest_id, fest_data))
                stats["checked_festivals"].append(fest_data["name"])
        
        if not matching_festivals:
            logger.info(f"No festive occasions today ({current_month}/{current_day})")
            return stats
        
        logger.info(f"🎉 Festive occasions today: {[f[1]['name'] for f in matching_festivals]}")
        
        # For each matching festival
        for fest_id, fest_data in matching_festivals:
            # Get all users who have enabled this festival
            settings_response = supabase.table("festive_email_settings").select("user_id").eq("festive_id", fest_id).eq("enabled", True).execute()
            
            if not settings_response.data:
                logger.info(f"No users have enabled {fest_data['name']}")
                continue
            
            enabled_user_ids = [s["user_id"] for s in settings_response.data]
            logger.info(f"Sending {fest_data['name']} emails to {len(enabled_user_ids)} users' leads")
            
            # Generate ONE premium email for this festival (reuse for all recipients)
            logger.info(f"🤖 Generating ONE AI-powered {fest_data['name']} email template...")
            
            # Use generic placeholders for AI generation
            ai_email_template = generate_premium_festive_email(
                festival_name=fest_data["name"],
                festival_description=fest_data.get("description", f"Celebrating {fest_data['name']}"),
                recipient_name="{{recipient_name}}",  # Placeholder
                agent_name="{{agent_name}}",  # Placeholder
                company_name="{{company}}",  # Placeholder
                city="{{city}}",  # Placeholder
                agent_specialty="real estate"
            )
            
            if ai_email_template and "subject" in ai_email_template and "body" in ai_email_template:
                logger.info(f"✨ Using AI-generated template for all {fest_data['name']} emails")
                # Store the AI-generated template
                ai_subject_template = ai_email_template["subject"]
                ai_body_template = ai_email_template["body"]
            else:
                logger.warning(f"AI generation failed, using static template for {fest_data['name']}")
                ai_subject_template = None
                ai_body_template = None
            
            # For each user with this festival enabled
            for user_id in enabled_user_ids:
                try:
                    # Get user profile for personalization
                    profile_response = supabase.table("profiles").select("full_name, company_name, markets").eq("id", user_id).single().execute()
                    
                    agent_name = "Your Agent"
                    company_name = "Your Company"
                    city = "your city"
                    
                    if profile_response.data:
                        agent_name = profile_response.data.get("full_name", agent_name)
                        company_name = profile_response.data.get("brokerage", company_name)
                        markets = profile_response.data.get("markets", [])
                        if markets and len(markets) > 0:
                            city = markets[0]
                    
                    # Get all active leads for this user (across all batches)
                    leads_response = supabase.table("leads").select("id, email, name").eq("user_id", user_id).eq("status", "active").execute()
                    
                    if not leads_response.data:
                        logger.info(f"No active leads for user {user_id}")
                        continue
                    
                    # Send email to each lead
                    for lead in leads_response.data:
                        try:
                            recipient_name = lead.get("name", "Friend")
                            recipient_email = lead["email"]
                            
                            # Use the pre-generated AI template or fallback to static template
                            if ai_subject_template and ai_body_template:
                                # Replace placeholders in the AI-generated template
                                subject = replace_email_placeholders(
                                    ai_subject_template,
                                    recipient_name=recipient_name,
                                    city=city,
                                    agent_name=agent_name,
                                    company=company_name
                                )
                                
                                body = replace_email_placeholders(
                                    ai_body_template,
                                    recipient_name=recipient_name,
                                    city=city,
                                    agent_name=agent_name,
                                    company=company_name
                                )
                            else:
                                # Fallback to static template
                                subject = replace_email_placeholders(
                                    fest_data["subject"],
                                    recipient_name=recipient_name,
                                    city=city,
                                    agent_name=agent_name,
                                    company=company_name
                                )
                                
                                body = replace_email_placeholders(
                                    fest_data["template"],
                                    recipient_name=recipient_name,
                                    city=city,
                                    agent_name=agent_name,
                                    company=company_name
                                )
                            
                            # Send via Mailgun
                            if mailgun_service:
                                result = mailgun_service.send_email(
                                    to_email=recipient_email,
                                    to_name=recipient_name,
                                    subject=subject,
                                    html_body=body.replace("\n", "<br>"),
                                    tags=[fest_id, "festive", "automated"]
                                )
                                
                                if result.get("success"):
                                    stats["emails_sent"] += 1
                                    logger.info(f"✅ Sent {fest_data['name']} email to {recipient_email}")
                                else:
                                    stats["emails_failed"] += 1
                                    stats["errors"].append(f"Failed to send to {recipient_email}")
                            else:
                                stats["emails_failed"] += 1
                                stats["errors"].append("Mailgun service not initialized")
                        
                        except Exception as lead_error:
                            stats["emails_failed"] += 1
                            error_msg = f"Error sending to lead {lead.get('email', 'unknown')}: {str(lead_error)}"
                            stats["errors"].append(error_msg)
                            logger.error(error_msg)
                
                except Exception as user_error:
                    error_msg = f"Error processing user {user_id}: {str(user_error)}"
                    stats["errors"].append(error_msg)
                    logger.error(error_msg)
        
        logger.info(f"🎊 Festive email sending complete: {stats['emails_sent']} sent, {stats['emails_failed']} failed")
        return stats
    
    except Exception as e:
        error_msg = f"Festive email cron failed: {str(e)}"
        logger.error(error_msg)
        stats["errors"].append(error_msg)
        return stats
