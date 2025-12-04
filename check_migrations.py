"""
Database Migration Checker
Run this to verify your database state before/after migrations.

Usage:
  source venv/bin/activate  # Activate virtual environment first
  python check_migrations.py
"""

import os
import sys
from typing import Dict, Any

try:
    from services.supabase_service import get_supabase_client
except ImportError as e:
    print("❌ Import error:", e)
    print("💡 Make sure to activate your virtual environment first:")
    print("   source venv/bin/activate")
    print("   pip install -r requirements.txt")
    sys.exit(1)

def check_database_state():
    """Check current database state for migration verification."""
    try:
        supabase = get_supabase_client()
        
        print("🔍 Checking Database State...")
        print("=" * 50)
        
        # Check campaigns table structure
        print("\n📋 Campaigns Table Structure:")
        try:
            # Try to fetch a sample campaign to see structure
            response = supabase.table('campaigns').select('*').limit(1).execute()
            
            if response.data:
                sample_campaign = response.data[0]
                print(f"✅ Campaigns table exists with {len(sample_campaign)} columns:")
                for key, value in sample_campaign.items():
                    print(f"   - {key}: {type(value).__name__}")
                
                # Check for persona vs tones
                if 'persona' in sample_campaign:
                    print(f"✅ 'persona' field found: {sample_campaign['persona']}")
                else:
                    print("❌ 'persona' field NOT found")
                    
                if 'tones' in sample_campaign:
                    print(f"⚠️  'tones' field still exists: {sample_campaign['tones']}")
                else:
                    print("✅ 'tones' field removed")
                    
            else:
                print("⚠️  No campaigns found, but table structure exists")
                
        except Exception as e:
            if "relation \"campaigns\" does not exist" in str(e):
                print("❌ Campaigns table does not exist")
            else:
                print(f"❌ Error checking campaigns: {e}")
        
        # Check other required tables
        print("\n📋 Other Required Tables:")
        required_tables = ['leads', 'batches', 'conversions']
        
        for table in required_tables:
            try:
                response = supabase.table(table).select('*').limit(1).execute()
                print(f"✅ {table} table exists")
            except Exception as e:
                if f'relation "{table}" does not exist' in str(e):
                    print(f"❌ {table} table missing")
                else:
                    print(f"⚠️  {table} table error: {e}")
        
        print("\n" + "=" * 50)
        print("Migration Status Summary:")
        print("📝 If 'persona' field exists → Migration 003 complete")
        print("📝 If 'persona' field missing → Run migration 003")
        print("📝 If any table missing → Run appropriate setup migration")
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        print("💡 Make sure your .env file has correct SUPABASE_URL and SUPABASE_KEY")

if __name__ == "__main__":
    # Add the project root to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    check_database_state()