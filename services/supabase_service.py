"""
Supabase database service for RealtyGenie
"""
import os
from typing import List, Optional
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Import supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase not installed. Install with: pip install supabase")

class SupabaseService:
    """Service for managing Supabase database operations"""
    
    def __init__(self):
        """Initialize Supabase client with admin role (service key)"""
        if not SUPABASE_AVAILABLE:
            raise RuntimeError("Supabase client is not installed")
        
        self.url = os.getenv("SUPABASE_URL", "").strip()
        self.key = os.getenv("SUPABASE_KEY", "").strip()
        
        if not self.url or not self.key:
            logger.error(f"SUPABASE_URL: {bool(self.url)}, SUPABASE_KEY: {bool(self.key)}")
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        
        try:
            logger.info(f"Initializing Supabase client with URL: {self.url[:50]}...")
            # Initialize with service key (admin role)
            self.client: Client = create_client(self.url, self.key)
            logger.info("✅ Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    def _get_client(self, user_token: Optional[str] = None) -> Client:
        """
        Get Supabase client - authenticated with JWT or using service role
        
        Args:
            user_token: Optional JWT token for user authentication
            
        Returns:
            Supabase client instance
        """
        if user_token:
            try:
                # Create a new client and set the JWT as the authorization header
                user_client = create_client(self.url, self.key)
                # Set the JWT token directly in the auth header
                user_client.postgrest.auth(user_token)
                logger.info("✅ Using authenticated user session with JWT")
                return user_client
            except Exception as e:
                logger.warning(f"Failed to set user session, falling back to service role: {e}")
                return self.client
        else:
            # Use admin client (service role)
            return self.client
    
    def insert_leads(self, leads: List[dict], batch_id: str, user_id: str, user_token: Optional[str] = None) -> tuple:
        """
        Insert cleaned leads into Supabase
        
        Args:
            leads: List of cleaned lead dictionaries
            batch_id: Batch ID to associate leads with
            user_id: User ID (from auth)
            user_token: Optional JWT token for authenticated insert
        
        Returns:
            Tuple of (inserted_leads, stats)
        """
        try:
            # Get appropriate client (authenticated or admin)
            client = self._get_client(user_token)
            
            # Add batch_id and user_id to each lead
            leads_to_insert = [
                {
                    **lead,
                    'batch_id': batch_id,
                    'user_id': user_id,
                    'status': 'active',
                }
                for lead in leads
            ]
            
            # Try bulk insert first
            try:
                response = client.table('leads').insert(leads_to_insert).execute()
                inserted_leads = response.data if response.data else []

                inserted_count = len(inserted_leads)
                logger.info(f"✅ Bulk insert successful: {inserted_count} leads inserted")

                # Update batch lead_count by incrementing with inserted_count
                try:
                    self.update_batch_lead_count(batch_id, count=inserted_count, increment=True)
                except Exception as e_upd:
                    logger.warning(f"Failed to update batch lead_count after bulk insert: {e_upd}")

                return inserted_leads, {
                    "inserted_count": inserted_count,
                    "skipped": 0,
                    "errors": 0
                }
            except Exception as bulk_error:
                # Fallback: insert one by one, skip duplicates
                logger.warning(f"Bulk insert failed, trying individual inserts: {bulk_error}")
                inserted_leads = []
                skipped = 0
                errors = 0
                
                for lead in leads_to_insert:
                    try:
                        response = client.table('leads').insert([lead]).execute()
                        if response.data:
                            inserted_leads.extend(response.data)
                            logger.info(f"✅ Inserted lead: {lead['email']}")
                    except Exception as lead_error:
                        error_str = str(lead_error).lower()
                        if "duplicate key" in error_str or "23505" in error_str:
                            skipped += 1
                            logger.info(f"⚠️  Skipped duplicate lead: {lead['email']}")
                        else:
                            errors += 1
                            logger.error(f"❌ Error inserting lead {lead['email']}: {lead_error}")
                
                inserted_count = len(inserted_leads)
                logger.info(f"Individual insert summary - inserted: {inserted_count}, skipped: {skipped}, errors: {errors}")

                # Update batch lead_count by incrementing with inserted_count
                try:
                    self.update_batch_lead_count(batch_id, count=inserted_count, increment=True)
                except Exception as e_upd:
                    logger.warning(f"Failed to update batch lead_count after individual inserts: {e_upd}")

                return inserted_leads, {
                    "inserted_count": inserted_count,
                    "skipped": skipped,
                    "errors": errors
                }
        
        except Exception as e:
            logger.error(f"Error inserting leads: {e}")
            raise
    
    def insert_single_lead(self, email: str, batch_id: str, user_id: str, name: Optional[str] = None, phone: Optional[str] = None, address: Optional[str] = None) -> dict:
        """
        Insert a single lead into Supabase
        
        Args:
            email: Lead email
            batch_id: Batch ID to associate with
            user_id: User ID (owner)
            name: Optional lead name
            phone: Optional lead phone
            address: Optional lead address
        
        Returns:
            Inserted lead data
        """
        try:
            lead_data = {
                "email": email,
                "name": name,
                "phone": phone,
                "address": address,
                "batch_id": batch_id,
                "user_id": user_id,
                "status": "active"
            }
            
            # Insert using service role
            response = self.client.table('leads').insert([lead_data]).execute()
            
            if response.data:
                inserted_lead = response.data[0]
                logger.info(f"✅ Single lead inserted: {email} to batch {batch_id}")
                
                # Increment batch lead count
                try:
                    self.update_batch_lead_count(batch_id, count=1, increment=True)
                except Exception as e_upd:
                    logger.warning(f"Failed to update batch lead_count after single insert: {e_upd}")
                
                return {
                    "success": True,
                    "lead": inserted_lead
                }
            else:
                raise Exception("No data returned from insert")
        
        except Exception as e:
            logger.error(f"Error inserting single lead {email}: {e}")
            raise
    
    def get_batch_leads_count(self, batch_id: str) -> int:
        """
        Get count of leads in a batch
        
        Args:
            batch_id: Batch ID
        
        Returns:
            Count of leads
        """
        try:
            # Method 1: Use Supabase exact count
            try:
                response = (
                    self.client.table("leads")
                    .select("id")              # don't pass count here
                    .eq("batch_id", batch_id)
                    .execute()    # ✅ count should be here
                )
                print(response)
                count = response.count or 0
                logger.info(f"🔍 Batch {batch_id}: Using count='exact' → {count} leads")
                return count

            except Exception as e1:
                logger.warning(f"⚠️ count='exact' method failed: {e1}")

                # Method 2: fallback manual count
                response = (
                    self.client.table("leads")
                    .select("id")
                    .eq("batch_id", batch_id)
                    .execute()
                )

                count = len(response.data) if response.data else 0
                logger.info(f"🔍 Batch {batch_id}: Using manual count → {count} leads")
                return count

        except Exception as e:
            logger.error(f"❌ Error fetching batch lead count: {e}")
            return 0
    
    def update_batch_lead_count(self, batch_id: str, count: Optional[int] = None, increment: bool = False, decrement: bool = False) -> dict:
        """
        Update the lead_count in batches table
        
        Args:
            batch_id: Batch ID
            count: Count value. If increment=True, adds to existing count. If decrement=True, subtracts from count. If both False, sets lead_count to count. If None, fetches actual count from leads.
            increment: If True, increments lead_count by count
            decrement: If True, decrements lead_count by count
        
        Returns:
            Updated batch data
        """
        try:
            # If count is not provided, fetch it from leads table
            if count is None:
                count = self.get_batch_leads_count(batch_id)
                logger.info(f"📊 Updating batch {batch_id} with total lead count: {count}")
                
                # Update the batches table with total count
                response = self.client.table('batches').update({
                    'lead_count': count
                }).eq('id', batch_id).execute()
                
                logger.info(f"✅ Successfully updated batch {batch_id} lead_count to {count}")
                
                return {
                    "success": True,
                    "batch_id": batch_id,
                    "lead_count": count
                }
            else:
                # Count is provided
                # Get current count
                current_batch = self.client.table('batches').select('lead_count').eq('id', batch_id).execute()
                if current_batch.data:
                    current_count = current_batch.data[0].get('lead_count', 0) or 0
                else:
                    current_count = 0
                
                # Calculate new count based on operation
                if increment:
                    new_count = current_count + count
                    logger.info(f"📊 Incrementing batch {batch_id} lead count: {current_count} + {count} = {new_count}")
                elif decrement:
                    new_count = max(0, current_count - count)  # Never go below 0
                    logger.info(f"📊 Decrementing batch {batch_id} lead count: {current_count} - {count} = {new_count}")
                else:
                    # Replace count
                    new_count = count
                    logger.info(f"📊 Setting batch {batch_id} lead count to {count}")
                
                # Update the batches table
                response = self.client.table('batches').update({
                    'lead_count': new_count
                }).eq('id', batch_id).execute()
                
                logger.info(f"✅ Successfully updated batch {batch_id} lead_count to {new_count}")
                
                return {
                    "success": True,
                    "batch_id": batch_id,
                    "lead_count": new_count
                }
        except Exception as e:
            logger.error(f"❌ Error updating batch lead count for {batch_id}: {e}")
            raise
    
    def check_duplicate_emails(self, emails: List[str], batch_id: Optional[str] = None) -> List[str]:
        """
        Check which emails already exist in database
        
        Args:
            emails: List of emails to check
            batch_id: Optional batch ID to check within specific batch
        
        Returns:
            List of duplicate emails
        """
        try:
            query = self.client.table('leads').select('email')
            
            if batch_id:
                query = query.eq('batch_id', batch_id)
            
            response = query.execute()
            
            existing_emails = {lead['email'].lower() for lead in response.data}
            duplicates = [email for email in emails if email.lower() in existing_emails]
            
            return duplicates
        except Exception as e:
            logger.error(f"Error checking duplicates: {e}")
            return []
    
    def _verify_lead_ownership(self, lead_id: str, user_id: str) -> bool:
        """
        Verify that a user owns a lead (manual authorization check)
        Uses service role to bypass RLS
        
        Args:
            lead_id: ID of lead to verify
            user_id: User ID to verify ownership
            
        Returns:
            True if user owns the lead, False otherwise
        """
        try:
            response = self.client.table('leads').select('user_id').eq('id', lead_id).execute()
            
            if not response.data:
                logger.warning(f"Lead {lead_id} not found")
                return False
            
            lead_user_id = response.data[0].get('user_id')
            owns_lead = lead_user_id == user_id
            
            logger.info(f"🔐 Lead ownership check: user_id={user_id}, lead_user_id={lead_user_id}, owns={owns_lead}")
            
            return owns_lead
        except Exception as e:
            logger.error(f"Error verifying lead ownership: {e}")
            return False
    
    def update_lead(self, lead_id: str, user_id: str, updates: dict) -> dict:
        """
        Update a lead (only if user owns it)
        
        Args:
            lead_id: ID of lead to update
            user_id: User ID (for authorization)
            updates: Dictionary of fields to update
        
        Returns:
            Updated lead data
        """
        try:
            logger.info(f"🔍 Attempting to update lead {lead_id} for user {user_id}")
            
            # Verify user owns this lead (manual check since we use service role)
            if not self._verify_lead_ownership(lead_id, user_id):
                logger.error(f"Lead {lead_id} not found or does not belong to user {user_id}")
                raise ValueError("Lead not found or access denied")
            
            # Update the lead using service role
            update_response = self.client.table('leads').update(updates).eq('id', lead_id).execute()
            
            logger.info(f"✅ Updated lead {lead_id}")
            
            if update_response.data:
                logger.info(f"Updated lead {lead_id} with data: {update_response.data[0]}")
                return {
                    "success": True,
                    "lead_id": lead_id,
                    "data": update_response.data[0]
                }
            else:
                # Update went through even if no data returned
                logger.info(f"✅ Lead {lead_id} updated (no data returned)")
                return {
                    "success": True,
                    "lead_id": lead_id,
                    "data": updates
                }
        
        except Exception as e:
            logger.error(f"Error updating lead {lead_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def delete_lead(self, lead_id: str, user_id: str) -> dict:
        """
        Delete a lead (only if user owns it)
        
        Args:
            lead_id: ID of lead to delete
            user_id: User ID (for authorization)
        
        Returns:
            Success confirmation with lead_id
        """
        try:
            logger.info(f"🔍 Attempting to delete lead {lead_id} for user {user_id}")
            
            # Get batch_id before deletion (for lead count update)
            batch_response = self.client.table('leads').select('batch_id').eq('id', lead_id).execute()
            
            if not batch_response.data:
                logger.error(f"Lead {lead_id} not found")
                raise ValueError("Lead not found")
            
            batch_id = batch_response.data[0]['batch_id']
            
            # Verify user owns this lead (manual check since we use service role)
            if not self._verify_lead_ownership(lead_id, user_id):
                logger.error(f"Lead {lead_id} does not belong to user {user_id}")
                raise ValueError("Lead not found or access denied")
            
            logger.info(f"✅ Lead verified - batch_id: {batch_id}")
            
            # Delete the lead using service role
            delete_response = self.client.table('leads').delete().eq('id', lead_id).execute()
            logger.info(f"✅ Lead deleted: {lead_id}")
            
            # Update batch lead count - decrement by 1
            try:
                self.update_batch_lead_count(batch_id, count=1, decrement=True)
            except Exception as e_upd:
                logger.warning(f"Failed to update batch lead_count after deletion: {e_upd}")
            
            logger.info(f"Deleted lead {lead_id} from batch {batch_id}")
            return {
                "success": True,
                "lead_id": lead_id,
                "batch_id": batch_id
            }
        
        except Exception as e:
            logger.error(f"Error deleting lead {lead_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def update_batch(self, batch_id: str, user_id: str, updates: dict) -> dict:
        """
        Update batch metadata (name, objective, tone_override, schedule_cadence)
        
        Args:
            batch_id: ID of batch to update
            user_id: User ID (for authorization)
            updates: Dictionary of fields to update
        
        Returns:
            Updated batch data
        """
        try:
            # First verify user owns this batch
            response = self.client.table('batches').select('id').eq('id', batch_id).eq('user_id', user_id).execute()
            
            if not response.data:
                logger.error(f"Batch {batch_id} not found or does not belong to user {user_id}")
                raise ValueError("Batch not found or access denied")
            
            # Update the batch
            update_response = self.client.table('batches').update(updates).eq('id', batch_id).execute()
            
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

# Global service instance
_supabase_service: Optional[SupabaseService] = None

def get_supabase_service() -> SupabaseService:
    """Get or create Supabase service instance"""
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
    return _supabase_service


def get_supabase_client():
    """Get Supabase client for direct table operations"""
    return get_supabase_service().client
