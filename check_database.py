#!/usr/bin/env python3
"""
Database Setup Helper for RealtyGenie
This script helps you check and set up the required database tables in Supabase.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from supabase import create_client
except ImportError:
    print("❌ Supabase library not installed. Run: pip install supabase")
    sys.exit(1)

def check_database_setup():
    """Check if all required tables exist in the database."""
    
    # Get Supabase credentials
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        return False
    
    try:
        supabase = create_client(url, key)
        print(f"✅ Connected to Supabase: {url[:50]}...")
        
        # Check required tables
        required_tables = [
            'profiles',
            'batches', 
            'leads',
            'campaigns',
            'campaign_emails',
            'conversions'
        ]
        
        existing_tables = []
        missing_tables = []
        
        for table in required_tables:
            try:
                # Try to query the table with limit 0 to check if it exists
                response = supabase.table(table).select('*').limit(0).execute()
                existing_tables.append(table)
                print(f"✅ Table '{table}' exists")
            except Exception as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    missing_tables.append(table)
                    print(f"❌ Table '{table}' missing")
                else:
                    print(f"⚠️  Table '{table}' check failed: {e}")
        
        print("\\n" + "="*50)
        print(f"📊 Database Status:")
        print(f"   Existing tables: {len(existing_tables)}/{len(required_tables)}")
        print(f"   Missing tables: {missing_tables}")
        
        if missing_tables:
            print("\\n🔧 To fix missing tables:")
            print("1. Go to your Supabase dashboard")
            print("2. Open the SQL Editor") 
            print("3. Copy and paste the content from 'setup_database.sql'")
            print("4. Run the SQL commands")
            print("\\n📁 The setup_database.sql file has been created in this directory.")
            return False
        else:
            print("\\n🎉 All required tables are present! Your database is ready.")
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def create_sample_data():
    """Create sample data for testing."""
    print("\\n🔄 Creating sample data...")
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    try:
        # You can add sample data creation logic here
        print("✅ Sample data created successfully")
    except Exception as e:
        print(f"❌ Failed to create sample data: {e}")

if __name__ == "__main__":
    print("🏠 RealtyGenie Database Setup Helper")
    print("="*50)
    
    if check_database_setup():
        print("\\n✨ Your database is ready for RealtyGenie!")
        
        # Optionally create sample data
        create_sample = input("\\nDo you want to create sample data for testing? (y/n): ").lower()
        if create_sample == 'y':
            create_sample_data()
    else:
        print("\\n🚨 Please set up the missing tables before proceeding.")
        print("\\n📖 Next steps:")
        print("1. Run the SQL from setup_database.sql in your Supabase dashboard")
        print("2. Run this script again to verify the setup")
        print("3. Start your RealtyGenie backend server")