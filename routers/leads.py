from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
from utils.cleaning import parse_csv_from_bytes, parse_excel_from_bytes, clean_leads_data
from utils.validation import is_valid_email, clean_email, clean_phone, clean_name, clean_address
from utils.google_sheets import fetch_google_sheet_as_csv
from services.supabase_service import get_supabase_service
from services.gemini_service import get_vision_service
import crud.leads as crud_leads

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/leads", tags=["leads"])

class Lead(BaseModel):
    email: str
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class CleanedLeadResponse(BaseModel):
    original_count: int
    cleaned_count: int
    invalid_emails: int
    duplicates_removed: int
    empty_rows: int
    cleaned_leads: List[Lead]

class ImportAndSaveResponse(BaseModel):
    success: bool
    message: str
    stats: dict
    inserted_leads: List[Lead]
    duplicate_info: Optional[dict] = None

@router.post("/clean", response_model=CleanedLeadResponse)
async def clean_leads(
    file: UploadFile = File(...),
    batch_id: str = Form(...)
):
    """
    Clean and validate leads from uploaded file (CSV or Excel)
    Returns cleaned leads without saving to database
    """
    try:
        content = await file.read()
        
        if file.filename.endswith('.csv'):
            df = parse_csv_from_bytes(content)
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = parse_excel_from_bytes(content)
        else:
            raise HTTPException(status_code=400, detail="File must be CSV or Excel format")
        
        cleaned_leads, stats = clean_leads_data(df)
        
        logger.info(f"Cleaned leads for batch {batch_id}: {stats}")
        
        return CleanedLeadResponse(
            original_count=stats['original_count'],
            cleaned_count=stats['cleaned_count'],
            invalid_emails=stats['invalid_emails'],
            duplicates_removed=stats['duplicates_removed'],
            empty_rows=stats['empty_rows'],
            cleaned_leads=[Lead(**lead) for lead in cleaned_leads]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning leads: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@router.post("/import-and-save", response_model=ImportAndSaveResponse)
async def import_and_save_leads(
    file: UploadFile = File(...),
    batch_id: str = Form(...),
    user_id: str = Form(...),
    user_token: Optional[str] = Form(None)
):
    """
    Clean leads from file, validate them, and save directly to Supabase
    Uses JWT token for authentication if provided
    """
    try:
        content = await file.read()
        
        if file.filename.endswith('.csv'):
            df = parse_csv_from_bytes(content)
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = parse_excel_from_bytes(content)
        else:
            raise HTTPException(status_code=400, detail="File must be CSV or Excel format")
        
        cleaned_leads, stats = clean_leads_data(df)
        
        if not cleaned_leads:
            raise HTTPException(status_code=400, detail="No valid leads found in file")
        
        supabase = get_supabase_service()
        client = supabase._get_client(user_token)
        
        inserted_leads, db_stats = crud_leads.insert_leads(
            client=client,
            leads=[{
                "email": lead["email"],
                "name": lead["name"],
                "phone": lead["phone"],
                "address": lead["address"],
            } for lead in cleaned_leads],
            batch_id=batch_id,
            user_id=user_id
        )
        
        logger.info(f"Insert stats - inserted: {db_stats['inserted_count']}, skipped: {db_stats['skipped']}, errors: {db_stats['errors']}")
        
        # Create success message with duplicate info if any
        if db_stats['skipped'] > 0:
            duplicate_list = []
            if 'duplicate_details' in db_stats and db_stats['duplicate_details']:
                for email, details in db_stats['duplicate_details'].items():
                    duplicate_list.append(f"'{email}' (already exists in batch '{details['existing_batch']}')") 
            
            duplicate_info = ", ".join(duplicate_list[:3])  # Show first 3
            if len(duplicate_list) > 3:
                duplicate_info += f" and {len(duplicate_list) - 3} more"
            
            message = f"Import completed: {db_stats['inserted_count']} leads added successfully. {db_stats['skipped']} duplicates skipped: {duplicate_info}"
        else:
            message = f"Successfully inserted {db_stats['inserted_count']} leads"
        
        return ImportAndSaveResponse(
            success=True,
            message=message,
            stats={
                "original_count": stats['original_count'],
                "cleaned_count": stats['cleaned_count'],
                "invalid_emails": stats['invalid_emails'],
                "duplicates_removed": stats['duplicates_removed'],
                "empty_rows": stats['empty_rows'],
                "inserted": db_stats['inserted_count'],
                "skipped_duplicates": db_stats['skipped'],
            },
            inserted_leads=[Lead(**lead) for lead in inserted_leads if lead],
            duplicate_info=db_stats.get('duplicate_details')
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing and saving leads: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.post("/import-from-url", response_model=ImportAndSaveResponse)
async def import_from_google_sheets(
    sheet_url: str = Form(...),
    batch_id: str = Form(...),
    user_id: str = Form(...),
    user_token: Optional[str] = Form(None)
):
    """
    Import leads from Google Sheets URL
    Sheet must be publicly accessible
    """
    try:
        logger.info(f"📊 Importing from Google Sheets: {sheet_url[:50]}...")
        csv_content = fetch_google_sheet_as_csv(sheet_url)
        
        if not csv_content:
            raise HTTPException(status_code=400, detail="Failed to fetch Google Sheet. Make sure the sheet is publicly accessible.")
        
        from io import BytesIO
        import pandas as pd
        
        try:
            df = pd.read_csv(BytesIO(csv_content))
            logger.info(f"✅ Parsed Google Sheet: {len(df)} rows")
        except Exception as parse_error:
            logger.error(f"❌ Error parsing Google Sheet CSV: {parse_error}")
            raise HTTPException(status_code=400, detail="Could not parse Google Sheet. Check the format.")
        
        cleaned_leads, stats = clean_leads_data(df)
        
        if not cleaned_leads:
            raise HTTPException(status_code=400, detail="No valid leads found in Google Sheet")
        
        # Get batch to check personas
        supabase = get_supabase_service()
        client = supabase._get_client(user_token)
        
        inserted_leads, db_stats = crud_leads.insert_leads(
            client=client,
            leads=[{
                "email": lead["email"],
                "name": lead["name"],
                "phone": lead["phone"],
                "address": lead["address"],
            } for lead in cleaned_leads],
            batch_id=batch_id,
            user_id=user_id
        )
        
        # Create success message with duplicate info if any
        if db_stats['skipped'] > 0:
            duplicate_list = []
            if 'duplicate_details' in db_stats and db_stats['duplicate_details']:
                for email, details in db_stats['duplicate_details'].items():
                    duplicate_list.append(f"'{email}' (already exists in batch '{details['existing_batch']}')") 
            
            duplicate_info = ", ".join(duplicate_list[:3])  # Show first 3
            if len(duplicate_list) > 3:
                duplicate_info += f" and {len(duplicate_list) - 3} more"
            
            message = f"Google Sheets import completed: {db_stats['inserted_count']} leads added successfully. {db_stats['skipped']} duplicates skipped: {duplicate_info}"
        else:
            message = f"Successfully imported and saved {db_stats['inserted_count']} leads from Google Sheets"
        
        return ImportAndSaveResponse(
            success=True,
            message=message,
            stats={
                "original_count": stats['original_count'],
                "cleaned_count": stats['cleaned_count'],
                "invalid_emails": stats['invalid_emails'],
                "duplicates_removed": stats['duplicates_removed'],
                "empty_rows": stats['empty_rows'],
                "inserted": db_stats['inserted_count'],
                "skipped_duplicates": db_stats['skipped'],
            },
            inserted_leads=[Lead(**lead) for lead in inserted_leads if lead],
            duplicate_info=db_stats.get('duplicate_details')
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing from Google Sheets: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.post("/import-from-photo", response_model=ImportAndSaveResponse)
async def import_from_photo(
    file: UploadFile = File(...),
    batch_id: str = Form(...),
    user_id: str = Form(...),
    user_token: Optional[str] = Form(None)
):
    """
    Import leads from photo/document using Google Vision API + Gemini AI
    Supports JPG, PNG, PDF formats
    """
    try:
        logger.info(f"📸 Processing image: {file.filename}")
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf']
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Supported formats: JPG, PNG, PDF"
            )
        
        # Read file content
        content = await file.read()
        
        # Process image with Vision API
        vision_service = get_vision_service()
        df = vision_service.process_image(content)
        
        logger.info(f"✅ Extracted {len(df)} contacts from image")
        
        if df.empty:
            raise HTTPException(
                status_code=400, 
                detail="No contact information found in the image. Please try a clearer photo."
            )
        
        # Clean the extracted data
        cleaned_leads, stats = clean_leads_data(df)
        
        if not cleaned_leads:
            raise HTTPException(
                status_code=400, 
                detail="No valid leads found after processing. Please ensure the image contains valid email addresses."
            )
        
        # Insert into database
        supabase = get_supabase_service()
        client = supabase._get_client(user_token)
        inserted_leads, db_stats = crud_leads.insert_leads(
            client=client,
            leads=[{
                "email": lead["email"],
                "name": lead["name"],
                "phone": lead["phone"],
                "address": lead["address"],
            } for lead in cleaned_leads],
            batch_id=batch_id,
            user_id=user_id
        )
        
        logger.info(f"✅ Inserted {db_stats['inserted_count']} leads from photo")
        
        # Create success message with duplicate info if any
        if db_stats['skipped'] > 0:
            duplicate_list = []
            if 'duplicate_details' in db_stats and db_stats['duplicate_details']:
                for email, details in db_stats['duplicate_details'].items():
                    duplicate_list.append(f"'{email}' (already exists in batch '{details['existing_batch']}')") 
            
            duplicate_info = ", ".join(duplicate_list[:3])  # Show first 3
            if len(duplicate_list) > 3:
                duplicate_info += f" and {len(duplicate_list) - 3} more"
            
            message = f"Photo import completed: {db_stats['inserted_count']} leads added successfully. {db_stats['skipped']} duplicates skipped: {duplicate_info}"
        else:
            message = f"Successfully extracted and saved {db_stats['inserted_count']} leads from photo"
        
        return ImportAndSaveResponse(
            success=True,
            message=message,
            stats={
                "original_count": stats['original_count'],
                "cleaned_count": stats['cleaned_count'],
                "invalid_emails": stats['invalid_emails'],
                "duplicates_removed": stats['duplicates_removed'],
                "empty_rows": stats['empty_rows'],
                "inserted": db_stats['inserted_count'],
                "skipped_duplicates": db_stats['skipped'],
            },
            inserted_leads=[Lead(**lead) for lead in inserted_leads if lead],
            duplicate_info=db_stats.get('duplicate_details')
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing from photo: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.post("/validate-single")
async def validate_email_endpoint(email: str):
    """Validate a single email"""
    is_valid = is_valid_email(email)
    return {
        "email": email,
        "is_valid": is_valid,
        "cleaned_email": clean_email(email) if is_valid else None
    }

@router.post("/check-duplicates")
async def check_duplicates(
    emails: List[str], 
    user_id: str,
    batch_id: Optional[str] = None
):
    """
    Check which emails already exist for a user before importing
    """
    try:
        if not emails:
            raise HTTPException(status_code=400, detail="No emails provided")
        
        supabase = get_supabase_service()
        duplicate_info = crud_leads.check_duplicate_emails(supabase.client, emails, user_id, batch_id)
        
        # Format detailed duplicate info with clear error messages
        detailed_duplicates = []
        for email, info in duplicate_info['details'].items():
            detailed_duplicates.append({
                'email': email,
                'existing_batch': info['batch_id'],
                'existing_name': info.get('name', 'No name'),
                'existing_id': info.get('id'),
                'error_message': f"Email '{email}' already exists in batch '{info['batch_id']}'"
            })
        
        return {
            "success": True,
            "total_emails": len(emails),
            "duplicate_count": len(duplicate_info['duplicates']),
            "unique_count": len(emails) - len(duplicate_info['duplicates']),
            "duplicates": duplicate_info['duplicates'],
            "duplicate_details": detailed_duplicates,
            "new_emails": [email for email in emails if email not in duplicate_info['duplicates']],
            "summary": f"Found {len(duplicate_info['duplicates'])} duplicates out of {len(emails)} emails checked"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking duplicates: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/validate-batch", response_model=CleanedLeadResponse)
async def validate_leads(leads: List[Lead]):
    """Validate and clean a list of leads"""
    try:
        if not leads:
            raise HTTPException(status_code=400, detail="No leads provided")
        
        original_count = len(leads)
        seen_emails = set()
        cleaned_leads = []
        stats = {
            'original_count': original_count,
            'invalid_emails': 0,
            'duplicates_removed': 0,
            'empty_rows': 0,
        }
        
        for lead in leads:
            email = lead.email.strip() if lead.email else ''
            
            if not email:
                stats['empty_rows'] += 1
                continue
            
            if not is_valid_email(email):
                stats['invalid_emails'] += 1
                continue
            
            email_cleaned = clean_email(email)
            
            if email_cleaned in seen_emails:
                stats['duplicates_removed'] += 1
                continue
            
            seen_emails.add(email_cleaned)
            
            cleaned_lead = {
                'email': email_cleaned,
                'name': clean_name(lead.name) if lead.name else None,
                'phone': clean_phone(lead.phone) if lead.phone else None,
                'address': clean_address(lead.address) if lead.address else None,
            }
            
            cleaned_leads.append(cleaned_lead)
        
        stats['cleaned_count'] = len(cleaned_leads)
        
        return CleanedLeadResponse(
            original_count=stats['original_count'],
            cleaned_count=stats['cleaned_count'],
            invalid_emails=stats['invalid_emails'],
            duplicates_removed=stats['duplicates_removed'],
            empty_rows=stats['empty_rows'],
            cleaned_leads=[Lead(**lead) for lead in cleaned_leads]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating leads: {e}")
        raise HTTPException(status_code=500, detail=f"Error validating leads: {str(e)}")


@router.put("/{lead_id}")
async def update_lead(
    lead_id: str,
    user_id: str,
    email: Optional[str] = None,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None
):
    """
    Update a lead (only if user owns it)
    """
    try:
        updates = {}
        if email is not None:
            updates['email'] = email
        if name is not None:
            updates['name'] = name
        if phone is not None:
            updates['phone'] = phone
        if address is not None:
            updates['address'] = address
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        supabase = get_supabase_service()
        result = crud_leads.update_lead(supabase.client, lead_id, user_id, updates)
        
        logger.info(f"Updated lead {lead_id} for user {user_id}")
        
        return {
            "success": True,
            "message": "Lead updated successfully",
            "lead_id": lead_id,
            "data": result["data"]
        }
    
    except Exception as e:
        logger.error(f"Error updating lead: {e}")
        if "access denied" in str(e).lower() or "not found" in str(e).lower():
            raise HTTPException(status_code=403, detail="Lead not found or access denied")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/add-single")
async def add_single_lead(
    email: str = Form(...),
    batch_id: str = Form(...),
    user_id: str = Form(...),
    name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None)
):
    """
    Add a single lead manually
    """
    try:
        logger.info(f"🎯 Adding single lead - email: {email}, batch_id: {batch_id}, user_id: {user_id}")
        
        if not is_valid_email(email):
            logger.error(f"Invalid email format: {email}")
            raise HTTPException(status_code=400, detail=f"Invalid email: {email}")
        
        email = clean_email(email)
        
        name = clean_name(name) if name else None
        phone = clean_phone(phone) if phone else None
        address = clean_address(address) if address else None
        
        logger.info(f"📝 Cleaned data - email: {email}, name: {name}, phone: {phone}")
        
        supabase = get_supabase_service()
        result = crud_leads.insert_single_lead(supabase.client, email, batch_id, user_id, name, phone, address)
        
        logger.info(f"✅ Successfully added lead {email} to batch {batch_id}")
        return {
            "success": True,
            "message": "Lead added successfully",
            "lead": result["lead"]
        }
    
    except HTTPException:
        raise
    except ValueError as ve:
        # Handle duplicate email validation error
        logger.warning(f"Duplicate email validation failed: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"❌ Error adding single lead - {type(e).__name__}: {str(e)}")
        if "duplicate key" in str(e).lower():
            raise HTTPException(status_code=400, detail=f"Lead with email '{email}' already exists")
        elif "foreign key" in str(e).lower():
            raise HTTPException(status_code=400, detail="Invalid batch_id or user_id provided")
        elif "permission denied" in str(e).lower() or "access denied" in str(e).lower():
            raise HTTPException(status_code=403, detail="Access denied - check user permissions")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, user_id: str):
    """
    Delete a lead (only if user owns it)
    """
    try:
        supabase = get_supabase_service()
        result = crud_leads.delete_lead(supabase.client, lead_id, user_id)
        
        logger.info(f"Deleted lead {lead_id} for user {user_id}")
        
        return {
            "success": True,
            "message": "Lead deleted successfully",
            "lead_id": lead_id,
            "batch_id": result["batch_id"]
        }
    
    except Exception as e:
        logger.error(f"Error deleting lead: {e}")
        if "access denied" in str(e).lower() or "not found" in str(e).lower():
            raise HTTPException(status_code=403, detail="Lead not found or access denied")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
