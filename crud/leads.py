"""CRUD operations for leads"""
import logging
from typing import List, Optional, Dict, Tuple
from supabase import Client

logger = logging.getLogger(__name__)


def check_duplicate_emails_in_batch(
    client: Client,
    emails: List[str],
    user_id: str,
    batch_id: str
) -> Dict[str, any]:
    """
    Check for duplicate emails within a specific batch only
    
    Args:
        client: Supabase client
        emails: List of emails to check
        user_id: User ID
        batch_id: Batch ID to check duplicates within
    
    Returns:
        Dictionary with duplicates and details
    """
    try:
        if not emails:
            return {'duplicates': [], 'details': {}}
        
        # Clean emails for comparison
        cleaned_emails = [email.lower().strip() for email in emails]
        
        # Query only leads within the specific batch
        response = client.table('leads').select(
            'id, email, name, batch_id'
        ).eq('user_id', user_id).eq('batch_id', batch_id).in_(
            'email', cleaned_emails
        ).execute()
        
        existing_leads = response.data if response.data else []
        
        # Build duplicate info
        duplicates = []
        details = {}
        
        for lead in existing_leads:
            email_lower = lead['email'].lower()
            duplicates.append(lead['email'])
            details[lead['email']] = {
                'batch_id': lead['batch_id'],
                'name': lead.get('name', 'No name'),
                'id': lead['id']
            }
        
        logger.info(f"Checked {len(emails)} emails in batch {batch_id}, found {len(duplicates)} duplicates")
        
        return {
            'duplicates': duplicates,
            'details': details
        }
        
    except Exception as e:
        logger.error(f"Error checking duplicate emails in batch: {e}")
        raise


def insert_leads(
    client: Client,
    leads: List[dict],
    batch_id: str,
    user_id: str
) -> Tuple[List[dict], dict]:
    """
    Insert multiple leads with duplicate validation
    
    Args:
        client: Supabase client (authenticated or service role)
        leads: List of lead dictionaries with email, name, phone, address
        batch_id: Batch ID to associate leads with
        user_id: User ID (owner)
    
    Returns:
        Tuple of (inserted_leads, stats_dict)
        stats_dict contains: inserted_count, skipped, errors, duplicate_details, duplicate_count
    """
    try:
        duplicate_details_formatted = {}
        
        # Pre-validate duplicates within the specific batch only
        if leads:
            emails_to_check = [lead['email'] for lead in leads if lead.get('email')]
            duplicate_check = check_duplicate_emails_in_batch(client, emails_to_check, user_id, batch_id)
            
            if duplicate_check['duplicates']:
                duplicate_emails_set = {email.lower() for email in duplicate_check['duplicates']}
                
                # Filter out duplicates
                leads_to_insert_filtered = [
                    {
                        **lead,
                        'batch_id': batch_id,
                        'user_id': user_id,
                        'status': 'active',
                    }
                    for lead in leads 
                    if lead['email'].lower() not in duplicate_emails_set
                ]
                
                skipped_count = len(leads) - len(leads_to_insert_filtered)
                
                # Create detailed duplicate error messages
                for email, info in duplicate_check['details'].items():
                    duplicate_details_formatted[email] = {
                        'email': email,
                        'existing_batch': info['batch_id'],
                        'existing_name': info.get('name', 'No name'),
                        'reason': f"Email '{email}' already exists in batch '{info['batch_id']}'"
                    }
                
                logger.info(f"Filtered out {skipped_count} duplicate leads with detailed reasons")
            else:
                # Add batch_id and user_id to each lead
                leads_to_insert_filtered = [
                    {
                        **lead,
                        'batch_id': batch_id,
                        'user_id': user_id,
                        'status': 'active',
                    }
                    for lead in leads
                ]
                skipped_count = 0
            
            # If no leads to insert after filtering
            if not leads_to_insert_filtered:
                logger.warning("No leads to insert after duplicate filtering")
                return [], {
                    "inserted_count": 0,
                    "skipped": len(leads),
                    "errors": 0,
                    "duplicate_details": duplicate_details_formatted,
                    "duplicate_count": len(leads)
                }
            
            # Try bulk insert first
            try:
                response = client.table('leads').insert(leads_to_insert_filtered).execute()
                inserted_leads = response.data if response.data else []

                inserted_count = len(inserted_leads)
                logger.info(f"✅ Bulk insert successful: {inserted_count} leads inserted")

                # Update batch lead_count by incrementing with inserted_count
                try:
                    update_batch_lead_count(client, batch_id, count=inserted_count, increment=True)
                except Exception as e_upd:
                    logger.warning(f"Failed to update batch lead_count after bulk insert: {e_upd}")

                return inserted_leads, {
                    "inserted_count": inserted_count,
                    "skipped": skipped_count,
                    "errors": 0,
                    "duplicate_details": duplicate_details_formatted if skipped_count > 0 else {},
                    "duplicate_count": skipped_count
                }
            except Exception as bulk_error:
                # Fallback: insert one by one, skip any remaining duplicates
                logger.warning(f"Bulk insert failed, trying individual inserts: {bulk_error}")
                inserted_leads = []
                additional_skipped = 0
                errors = 0
                
                for lead in leads_to_insert_filtered:
                    try:
                        response = client.table('leads').insert([lead]).execute()
                        if response.data:
                            inserted_leads.extend(response.data)
                            logger.info(f"✅ Inserted lead: {lead['email']}")
                    except Exception as lead_error:
                        error_str = str(lead_error).lower()
                        if "duplicate key" in error_str or "23505" in error_str:
                            additional_skipped += 1
                            logger.info(f"⚠️  Skipped duplicate lead: {lead['email']}")
                        else:
                            errors += 1
                            logger.error(f"❌ Error inserting lead {lead['email']}: {lead_error}")
                
                inserted_count = len(inserted_leads)
                total_skipped = skipped_count + additional_skipped
                logger.info(f"Individual insert summary - inserted: {inserted_count}, skipped: {total_skipped}, errors: {errors}")

                # Update batch lead_count by incrementing with inserted_count
                try:
                    update_batch_lead_count(client, batch_id, count=inserted_count, increment=True)
                except Exception as e_upd:
                    logger.warning(f"Failed to update batch lead_count after individual inserts: {e_upd}")

                return inserted_leads, {
                    "inserted_count": inserted_count,
                    "skipped": total_skipped,
                    "errors": errors,
                    "duplicate_details": duplicate_details_formatted if total_skipped > 0 else {},
                    "duplicate_count": total_skipped
                }
        
    except Exception as e:
        logger.error(f"Error inserting leads: {e}")
        raise


def insert_single_lead(
    client: Client,
    email: str,
    batch_id: str,
    user_id: str,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None
) -> dict:
    """
    Insert a single lead with duplicate validation
    
    Args:
        client: Supabase client
        email: Lead email
        batch_id: Batch ID to associate with
        user_id: User ID (owner)
        name: Optional lead name
        phone: Optional lead phone
        address: Optional lead address
    
    Returns:
        Dict with success status and lead data
    """
    try:
        # Check if email already exists in the specific batch only
        duplicate_check = check_duplicate_emails_in_batch(client, [email], user_id, batch_id)
        
        if duplicate_check['duplicates']:
            existing_lead = duplicate_check['details'][email]
            error_msg = f"Email '{email}' already exists in this batch"
            if existing_lead.get('name'):
                error_msg += f" (Lead name: {existing_lead['name']})"
            
            logger.warning(f"Duplicate email attempted in batch {batch_id}: {email} for user {user_id}")
            raise ValueError(error_msg)
        
        lead_data = {
            "email": email,
            "name": name,
            "phone": phone,
            "address": address,
            "batch_id": batch_id,
            "user_id": user_id,
            "status": "active"
        }
        
        # Insert using provided client
        response = client.table('leads').insert([lead_data]).execute()
        
        if response.data:
            inserted_lead = response.data[0]
            logger.info(f"✅ Single lead inserted: {email} to batch {batch_id}")
            
            # Increment batch lead count
            try:
                update_batch_lead_count(client, batch_id, count=1, increment=True)
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


def check_duplicate_emails(
    client: Client,
    emails: List[str],
    user_id: str,
    batch_id: Optional[str] = None
) -> dict:
    """
    Check which emails already exist for a user
    
    Args:
        client: Supabase client
        emails: List of emails to check
        user_id: User ID to scope the check
        batch_id: Optional batch ID to check within specific batch
    
    Returns:
        Dict with duplicates list and details dict
    """
    try:
        query = client.table('leads').select('email, name, batch_id, id').eq('user_id', user_id)
        
        if batch_id:
            query = query.eq('batch_id', batch_id)
        
        response = query.execute()
        
        existing_leads = {lead['email'].lower(): lead for lead in response.data}
        duplicates = []
        details = {}
        
        for email in emails:
            email_lower = email.lower()
            if email_lower in existing_leads:
                duplicates.append(email)
                details[email] = existing_leads[email_lower]
        
        return {
            'duplicates': duplicates,
            'details': details
        }
    except Exception as e:
        logger.error(f"Error checking duplicates: {e}")
        return {'duplicates': [], 'details': {}}


def check_single_email_exists(
    client: Client,
    email: str,
    user_id: str,
    batch_id: Optional[str] = None
) -> dict:
    """
    Check if a single email exists for a user
    
    Args:
        client: Supabase client
        email: Email to check
        user_id: User ID to scope the check
        batch_id: Optional batch ID to exclude from check (for updates)
    
    Returns:
        Dict with exists boolean and lead_info
    """
    try:
        query = client.table('leads').select('*').eq('user_id', user_id).eq('email', email)
        
        if batch_id:
            # Exclude the current batch when checking (useful for updates)
            query = query.neq('batch_id', batch_id)
        
        response = query.execute()
        
        if response.data:
            return {
                'exists': True,
                'lead_info': response.data[0]
            }
        else:
            return {
                'exists': False,
                'lead_info': None
            }
    except Exception as e:
        logger.error(f"Error checking email existence: {e}")
        return {'exists': False, 'lead_info': None}


def verify_lead_ownership(client: Client, lead_id: str, user_id: str) -> bool:
    """
    Verify that a user owns a lead
    
    Args:
        client: Supabase client (should be service role for RLS bypass)
        lead_id: ID of lead to verify
        user_id: User ID to verify ownership
        
    Returns:
        True if user owns the lead, False otherwise
    """
    try:
        response = client.table('leads').select('user_id').eq('id', lead_id).execute()
        
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


def update_lead(client: Client, lead_id: str, user_id: str, updates: dict) -> dict:
    """
    Update a lead (only if user owns it)
    
    Args:
        client: Supabase client
        lead_id: ID of lead to update
        user_id: User ID (for authorization)
        updates: Dictionary of fields to update
    
    Returns:
        Dict with success status and updated data
    """
    try:
        logger.info(f"🔍 Attempting to update lead {lead_id} for user {user_id}")
        
        # Verify user owns this lead
        if not verify_lead_ownership(client, lead_id, user_id):
            logger.error(f"Lead {lead_id} not found or does not belong to user {user_id}")
            raise ValueError("Lead not found or access denied")
        
        # Update the lead
        update_response = client.table('leads').update(updates).eq('id', lead_id).execute()
        
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


def delete_lead(client: Client, lead_id: str, user_id: str) -> dict:
    """
    Delete a lead (only if user owns it)
    
    Args:
        client: Supabase client
        lead_id: ID of lead to delete
        user_id: User ID (for authorization)
    
    Returns:
        Dict with success status, lead_id, and batch_id
    """
    try:
        logger.info(f"🔍 Attempting to delete lead {lead_id} for user {user_id}")
        
        # Get batch_id before deletion (for lead count update)
        batch_response = client.table('leads').select('batch_id').eq('id', lead_id).execute()
        
        if not batch_response.data:
            logger.error(f"Lead {lead_id} not found")
            raise ValueError("Lead not found")
        
        batch_id = batch_response.data[0]['batch_id']
        
        # Verify user owns this lead
        if not verify_lead_ownership(client, lead_id, user_id):
            logger.error(f"Lead {lead_id} does not belong to user {user_id}")
            raise ValueError("Lead not found or access denied")
        
        logger.info(f"✅ Lead verified - batch_id: {batch_id}")
        
        # Delete the lead
        delete_response = client.table('leads').delete().eq('id', lead_id).execute()
        logger.info(f"✅ Lead deleted: {lead_id}")
        
        # Update batch lead count - decrement by 1
        try:
            update_batch_lead_count(client, batch_id, count=1, decrement=True)
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


def get_batch_leads_count(client: Client, batch_id: str) -> int:
    """
    Get count of leads in a batch
    
    Args:
        client: Supabase client
        batch_id: Batch ID
    
    Returns:
        Count of leads
    """
    try:
        # Method 1: Use Supabase exact count
        try:
            response = (
                client.table("leads")
                .select("id")
                .eq("batch_id", batch_id)
                .execute()
            )
            count = response.count or 0
            logger.info(f"🔍 Batch {batch_id}: Using count='exact' → {count} leads")
            return count

        except Exception as e1:
            logger.warning(f"⚠️ count='exact' method failed: {e1}")

            # Method 2: fallback manual count
            response = (
                client.table("leads")
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


def update_batch_lead_count(
    client: Client,
    batch_id: str,
    count: Optional[int] = None,
    increment: bool = False,
    decrement: bool = False
) -> dict:
    """
    Update the lead_count in batches table
    
    Args:
        client: Supabase client
        batch_id: Batch ID
        count: Count value. If increment=True, adds to existing. If decrement=True, subtracts. 
               If both False, sets lead_count to count. If None, fetches actual count from leads.
        increment: If True, increments lead_count by count
        decrement: If True, decrements lead_count by count
    
    Returns:
        Dict with success status, batch_id, and lead_count
    """
    try:
        # If count is not provided, fetch it from leads table
        if count is None:
            count = get_batch_leads_count(client, batch_id)
            logger.info(f"📊 Updating batch {batch_id} with total lead count: {count}")
            
            # Update the batches table with total count
            response = client.table('batches').update({
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
            current_batch = client.table('batches').select('lead_count').eq('id', batch_id).execute()
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
            response = client.table('batches').update({
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
