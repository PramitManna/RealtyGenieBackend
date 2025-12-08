"""Campaign Email Service - Handles generation, approval, and scheduling of campaign emails"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from services.supabase_service import get_supabase_client
from services.gemini_service import GeminiService

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

# Email categories matching frontend
MONTH_1_CATEGORIES = [
    {
        'id': 'introduction',
        'name': 'Introduction Email',
        'prompt': 'Create a warm introduction email that establishes credibility and sets expectations for future communication. Introduce yourself as a real estate professional, highlight your expertise in the target city, and explain the value you provide.',
        'send_day': 0,
        'order': 1,
    },
    {
        'id': 'market_insight',
        'name': 'Market Insight',
        'prompt': 'Provide current market trends and data specific to the target city real estate market. Include statistics, recent sales data, and what this means for buyers/sellers/investors.',
        'send_day': 5,
        'order': 2,
    },
    {
        'id': 'education_process',
        'name': 'Education / Process',
        'prompt': 'Educate leads about the buying/selling/investing process with actionable tips. Break down the step-by-step process, common mistakes to avoid, and insider tips that demonstrate your expertise.',
        'send_day': 10,
        'order': 3,
    },
    {
        'id': 'value_offer',
        'name': 'Value Offer',
        'prompt': 'Present a specific value proposition or exclusive opportunity. Offer a free market analysis, exclusive listing preview, or personalized consultation. Make it time-sensitive to encourage action.',
        'send_day': 16,
        'order': 4,
    },
    {
        'id': 'case_study',
        'name': 'Case Study / Credibility',
        'prompt': 'Share a success story or case study demonstrating your expertise and results. Tell a compelling story about how you helped a client, including specific numbers and outcomes.',
        'send_day': 22,
        'order': 5,
    },
]


class CampaignEmailService:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.gemini_service = GeminiService()
    
    def generate_month_1_emails(
        self,
        campaign_id: str,
        campaign_name: str,
        tones: List[str],
        objective: str,
        agent_name: str = "Your Name",
        company_name: str = "Your Company",
        target_city: str = "your market",
        persona: str = "buyer",
    ) -> List[Dict]:
        """
        Generate 5 Month 1 emails using Gemini AI
        Uses automatic persona-to-tone mapping
        Returns list of draft emails (not saved to DB yet)
        """
        logger.info(f"Generating Month 1 emails for campaign {campaign_id} with persona: {persona}")
        
        generated_emails = []
        
        for category in MONTH_1_CATEGORIES:
            try:
                # Generate email using Gemini service (handles all prompt building)
                email_response = self.gemini_service.generate_single_email(
                    category_prompt=category['prompt'],
                    campaign_context={
                        'campaign_name': campaign_name,
                        'tones': tones,  # Pass all tones for blending
                        'objective': objective,
                        'agent_name': agent_name,
                        'company_name': company_name,
                        'target_city': target_city,
                    }
                )
                
                email = {
                    'category_id': category['id'],
                    'category_name': category['name'],
                    'subject': email_response['subject'],
                    'body': email_response['body'],
                    'send_day': category['send_day'],
                    'order': category['order'],
                    'month_phase': 'month_1',
                    'month_number': 1,
                    'metadata': email_response.get('metadata', {}),  # Token usage
                }
                
                generated_emails.append(email)
                logger.info(f"Generated email for category: {category['id']} | Tokens: {email_response.get('metadata', {}).get('total_tokens', 'N/A')}")
                
            except Exception as e:
                logger.error(f"Error generating email for category {category['id']}: {e}")
                raise Exception(f"Failed to generate {category['name']}: {str(e)}")
        
        return generated_emails
    
    def save_approved_emails(
        self,
        campaign_id: str,
        user_id: str,
        emails: List[Dict],
        campaign_start_date: Optional[datetime] = None,
    ) -> Dict:
        
        if not campaign_start_date:
            campaign_start_date = datetime.utcnow()
        
        logger.info(f"Saving {len(emails)} approved emails for campaign {campaign_id}")
        
        existing_response = self.supabase.table('campaign_emails').select('id, category_id').eq('batch_id', campaign_id).execute()
        existing_emails = {e['category_id']: e['id'] for e in (existing_response.data or [])}
        
        if existing_emails:
            logger.warning(f"⚠️  Found {len(existing_emails)} existing emails for campaign {campaign_id}. Skipping save.")
            logger.info(f"Existing categories: {list(existing_emails.keys())}")
            return {
                'success': False,
                'campaign_id': campaign_id,
                'message': 'Emails already saved for this campaign. Launch skipped to prevent duplicates.',
                'existing_count': len(existing_emails),
            }
        
        email_records = []
        for email in emails:
            send_offset = email['send_day']
            scheduled_date = campaign_start_date + timedelta(days=send_offset)
            
            scheduled_date = scheduled_date.replace(hour=11, minute=0, second=0, microsecond=0)
            
            record = {
                'batch_id': campaign_id,
                'user_id': user_id,
                'category_id': email['category_id'],
                'category_name': email['category_name'],
                'subject': email['subject'],
                'body': email['body'],
                'send_day': email['send_day'],
                'scheduled_send_date': scheduled_date.isoformat(),
                'status': 'approved',
                'month_phase': email.get('month_phase', 'month_1'),
                'month_number': email.get('month_number', 1),
                'email_order': email.get('order', email['send_day']),
                'metadata': email.get('metadata', {}),  # Save token usage metadata
            }
            
            email_records.append(record)
        
        # Insert into database
        try:
            response = self.supabase.table('campaign_emails').insert(email_records).execute()
            
            # Update batch status to active and save start date (campaign_id is actually batch_id)
            self.supabase.table('batches').update({
                'start_date': campaign_start_date.isoformat(),
                'updated_at': campaign_start_date.isoformat(),
                'status': 'active',  # Activate batch automation
            }).eq('id', campaign_id).execute()
            
            self._queue_emails_for_sending(campaign_id, response.data or email_records, campaign_start_date)
            
            logger.info(f"Successfully saved {len(email_records)} emails for batch {campaign_id}")
            
            return {
                'success': True,
                'campaign_id': campaign_id,
                'emails_saved': len(email_records),
                'campaign_start_date': campaign_start_date.isoformat(),
                'emails': response.data,
                'queued': True,
            }
            
        except Exception as e:
            logger.error(f"Error saving approved emails: {e}")
            raise Exception(f"Failed to save emails: {str(e)}")
    
    def _queue_emails_for_sending(
        self,
        campaign_id: str,  # This is actually a batch_id now
        emails: List[Dict],
        campaign_start_date: datetime,
    ) -> None:
        """
        Queue approved emails for all leads in batch.
        Simple: For each email × each lead, create a queue entry.
        """
        try:
            # campaign_id is actually batch_id (we pass batch_id directly now)
            batch_id = campaign_id
            logger.info(f"📦 Queuing emails for Batch {batch_id}")
            
            # Get all leads from batch
            leads_response = self.supabase.table('leads').select('id, email, name').eq('batch_id', batch_id).execute()
            leads = leads_response.data or []
            
            if not leads:
                logger.warning(f"⚠️  No leads in batch {batch_id}")
                return
            
            logger.info(f"📋 Found {len(leads)} leads")
            
            queue_entries = []
            day_0_queue_entries = []  # Track Day 0 entries for immediate sending
            
            # For each email, create queue entry for each lead
            for email in emails:
                if email['send_day'] == 0:
                    # Day 0: Send immediately (set to 1 hour ago to ensure it's picked up by cron right away)
                    scheduled_date = datetime.utcnow() - timedelta(hours=1)
                else:
                    # Day 5+: Schedule for 9 AM on that day
                    scheduled_date = campaign_start_date + timedelta(days=email['send_day'])
                    scheduled_date = scheduled_date.replace(hour=9, minute=0, second=0, microsecond=0)
                
                for lead in leads:
                    queue_entry = {
                        'campaign_id': campaign_id,
                        'lead_id': lead['id'],
                        'recipient_email': lead['email'],
                        'recipient_name': lead.get('name', 'Recipient'),
                        'send_day': email['send_day'],
                        'scheduled_for': scheduled_date.isoformat(),
                        'status': 'pending',
                    }
                    queue_entries.append(queue_entry)
                    if email['send_day'] == 0:
                        day_0_queue_entries.append(queue_entry)
            
            # Insert all queue entries
            if queue_entries:
                insert_response = self.supabase.table('campaign_send_queue').insert(queue_entries).execute()
                logger.info(f"✅ Queued {len(queue_entries)} sends ({len(leads)} leads × {len(emails)} emails)")
            
            # Send Day 0 emails immediately
            if day_0_queue_entries:
                # Fetch the actual queue entries with IDs from database
                day_0_queued = self.supabase.table('campaign_send_queue').select('*').eq('campaign_id', campaign_id).eq('send_day', 0).eq('status', 'pending').execute()
                if day_0_queued.data:
                    self._send_day_0_emails_immediately(campaign_id, day_0_queued.data)
            
        except Exception as e:
            logger.error(f"Error queuing: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def get_campaign_emails(self, campaign_id: str) -> List[Dict]:
        """Get all emails for a campaign"""
        try:
            response = self.supabase.table('campaign_emails').select('*').eq('campaign_id', campaign_id).order('email_order').execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching campaign emails: {e}")
            return []
    
    def update_email(
        self,
        email_id: str,
        subject: Optional[str] = None,
        body: Optional[str] = None,
    ) -> Dict:
        """Update an email's subject or body"""
        try:
            updates = {}
            if subject is not None:
                updates['subject'] = subject
            if body is not None:
                updates['body'] = body
            
            response = self.supabase.table('campaign_emails').update(updates).eq('id', email_id).execute()
            
            return {
                'success': True,
                'email_id': email_id,
                'updated': response.data,
            }
        except Exception as e:
            logger.error(f"Error updating email: {e}")
            raise Exception(f"Failed to update email: {str(e)}")
    
    def _send_day_0_emails_immediately(self, campaign_id: str, queue_entries: List[Dict]) -> None:
        """
        Send Day 0 emails immediately instead of waiting for cron.
        This ensures the first introduction email goes out right away when campaign launches.
        """
        try:
            from services.mailgun_service import mailgun_service
            
            # Get the Day 0 email content
            email_response = self.supabase.table('campaign_emails').select('subject, body, user_id').eq('campaign_id', campaign_id).eq('send_day', 0).single().execute()
            
            if not email_response.data:
                logger.warning(f"⚠️  Day 0 email not found for campaign {campaign_id}")
                return
            
            email_data = email_response.data
            
            # Get agent info from user profile
            agent_name = "Your Agent"
            company_name = "Your Company"
            city = "your city"
            
            try:
                user_id = email_data.get('user_id')
                if user_id:
                    profile_response = self.supabase.table('profiles').select('full_name, company_name, markets').eq('id', user_id).single().execute()
                    if profile_response.data:
                        agent_name = profile_response.data.get('full_name', agent_name)
                        company_name = profile_response.data.get('brokerage', company_name)
                        markets = profile_response.data.get('markets', [])
                        if markets and len(markets) > 0:
                            city = markets[0]
            except Exception as e:
                logger.warning(f"Could not fetch profile: {e}")
            
            sent_count = 0
            failed_count = 0
            
            # Send to each lead
            for queue_entry in queue_entries:
                try:
                    recipient_name = queue_entry.get('recipient_name', 'Recipient')
                    
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
                    
                    logger.info(f"📧 Sending Day 0 email instantly to {queue_entry['recipient_email']}")
                    
                    result = mailgun_service.send_email(
                        to_email=queue_entry['recipient_email'],
                        to_name=recipient_name,
                        subject=personalized_subject,
                        html_body=personalized_body,
                        tags=['day_0', 'campaign', 'instant'],
                    )
                    
                    # Mark as sent in queue
                    self.supabase.table('campaign_send_queue').update({
                        'status': 'sent',
                        'sent_at': datetime.utcnow().isoformat(),
                    }).eq('id', queue_entry['id']).execute()
                    
                    logger.info(f"✅ Day 0 email sent to {queue_entry['recipient_email']}")
                    sent_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to send Day 0 to {queue_entry['recipient_email']}: {str(e)}")
                    failed_count += 1
                    
                    # Mark as failed in queue
                    try:
                        self.supabase.table('campaign_send_queue').update({
                            'status': 'failed',
                            'error_message': str(e)[:255],
                        }).eq('id', queue_entry['id']).execute()
                    except:
                        pass
            
            logger.info(f"🚀 Day 0 instant send complete: {sent_count} sent, {failed_count} failed")
            
        except Exception as e:
            logger.error(f"Error in instant Day 0 sending: {e}")
            import traceback
            logger.error(traceback.format_exc())
