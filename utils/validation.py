import re

def is_valid_email(email: str) -> bool:
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email.strip().lower()) is not None

def clean_email(email: str) -> str:
    """Clean and normalize email"""
    if not email:
        return ""
    return email.strip().lower()

def clean_phone(phone: str) -> str:
    """Clean phone number - remove special chars but keep digits"""
    if not phone:
        return ""
    cleaned = re.sub(r'\D', '', str(phone))
    return cleaned if len(cleaned) >= 7 else ""

def clean_name(name: str) -> str:
    """Clean name - remove extra spaces and normalize"""
    if not name:
        return ""
    name = str(name).strip()
    name = ' '.join(name.split())
    return name.title() if name else ""

def clean_address(address: str) -> str:
    """Clean address - remove extra spaces"""
    if not address:
        return ""
    address = str(address).strip()
    address = ' '.join(address.split())
    return address
