"""
Supabase client service - provides database client access

All CRUD operations have been moved to crud/ modules:
- crud.leads - Lead operations (insert, update, delete, duplicate checking)
- crud.batches - Batch operations (update)

This service provides only:
- Client initialization with service role
- Client retrieval with user authentication
"""
import os
from typing import Optional
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
    """
    Thin service for Supabase client management
    Provides database client with service role or user authentication
    """
    
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
            logger.info(" Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    def _get_client(self, user_token: Optional[str] = None) -> Client:
        """
        Get Supabase client with appropriate authentication
        
        Args:
            user_token: Optional JWT token for user authentication
                       If provided, creates authenticated client for user operations
                       If None, uses service role client (admin access, bypasses RLS)
        
        Returns:
            Authenticated Supabase client
        """
        if user_token:
            # Create a user-authenticated client
            # This respects RLS policies for the authenticated user
            user_client = create_client(self.url, self.key)
            user_client.postgrest.auth(user_token)
            logger.info(" Using user-authenticated client")
            return user_client
        
        # Use service role client (admin, bypasses RLS)
        logger.info(" Using service role client (admin)")
        return self.client


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

