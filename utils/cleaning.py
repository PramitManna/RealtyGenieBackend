import pandas as pd
import io
import logging
from fastapi import HTTPException
from typing import Tuple, List, Dict
from utils.validation import (
    is_valid_email, clean_email, clean_phone, 
    clean_name, clean_address
)

logger = logging.getLogger(__name__)

def parse_csv_from_bytes(file_content: bytes) -> pd.DataFrame:
    """Parse CSV file from bytes"""
    try:
        df = pd.read_csv(io.BytesIO(file_content))
        return df
    except Exception as e:
        logger.error(f"Error parsing CSV: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid CSV file: {str(e)}")

def parse_excel_from_bytes(file_content: bytes) -> pd.DataFrame:
    """Parse Excel file from bytes"""
    try:
        df = pd.read_excel(io.BytesIO(file_content))
        return df
    except Exception as e:
        logger.error(f"Error parsing Excel: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid Excel file: {str(e)}")

def detect_column_mappings(df: pd.DataFrame) -> dict:
    """Detect email, name, phone, address columns from headers"""
    headers = [col.lower().strip() for col in df.columns]
    
    mappings = {
        'email': None,
        'name': None,
        'phone': None,
        'address': None,
    }
    
    # Validate that required columns exist
    required_columns = {'email', 'name'}
    
    # Email column detection
    email_keywords = ['email', 'e-mail', 'email_address', 'emailaddress']
    for idx, header in enumerate(headers):
        for keyword in email_keywords:
            if keyword in header:
                mappings['email'] = df.columns[idx]
                break
    
    # Name column detection
    name_keywords = ['name', 'full_name', 'fullname', 'contact_name', 'contactname', 'first_name', 'firstname']
    for idx, header in enumerate(headers):
        for keyword in name_keywords:
            if keyword in header:
                mappings['name'] = df.columns[idx]
                break
    
    # Phone column detection
    phone_keywords = ['phone', 'phone_number', 'phonenumber', 'mobile', 'mobile_number', 'mobilenumber', 'telephone', 'tel']
    for idx, header in enumerate(headers):
        for keyword in phone_keywords:
            if keyword in header:
                mappings['phone'] = df.columns[idx]
                break
    
    # Address column detection
    address_keywords = ['address', 'street', 'street_address', 'streetaddress', 'location', 'city', 'full_address', 'fulladdress']
    for idx, header in enumerate(headers):
        for keyword in address_keywords:
            if keyword in header:
                mappings['address'] = df.columns[idx]
                break
    
    return mappings

def clean_leads_data(df: pd.DataFrame) -> Tuple[List[dict], dict]:
    """
    Clean and validate leads data
    Returns: (cleaned_leads, statistics)
    """
    if df.empty:
        raise HTTPException(status_code=400, detail="File is empty")
    
    original_count = len(df)
    seen_emails = set()
    cleaned_leads = []
    stats = {
        'original_count': original_count,
        'invalid_emails': 0,
        'duplicates_removed': 0,
        'empty_rows': 0,
    }
    
    mappings = detect_column_mappings(df)
    
    logger.info(f"Column mappings detected: {mappings}")
    
    if not mappings['email']:
        raise HTTPException(status_code=400, detail="Email column is required. Please include an 'email' column in your file.")
    
    if not mappings['name']:
        raise HTTPException(status_code=400, detail="Name column is required. Please include a 'name' column in your file.")
    
    for _, row in df.iterrows():
        email = str(row.get(mappings['email'], '')).strip() if mappings['email'] else ''
        name = str(row.get(mappings['name'], '')).strip() if mappings['name'] else ''
        
        if not email or pd.isna(email):
            stats['empty_rows'] += 1
            continue
        
        if not name or pd.isna(name):
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
        
        phone = str(row.get(mappings['phone'], '')).strip() if mappings['phone'] else ''
        address = str(row.get(mappings['address'], '')).strip() if mappings['address'] else ''
        
        lead = {
            'email': email_cleaned,
            'name': clean_name(name) or None,
            'phone': clean_phone(phone) or None,
            'address': clean_address(address) or None,
        }
        
        cleaned_leads.append(lead)
    
    stats['cleaned_count'] = len(cleaned_leads)
    
    return cleaned_leads, stats
