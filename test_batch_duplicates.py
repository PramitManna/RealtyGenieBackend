#!/usr/bin/env python3
"""
Test script to verify batch-specific duplicate validation
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_batch_duplicate_validation():
    """Test that same email can exist in different batches"""
    
    # Sample data - this should represent your actual test data
    test_email = "pramitmanna19@gmail.com"
    test_name = "Pramit Manna"
    test_phone = "1234567890"
    user_id = "53c06748-9223-4eca-ab1e-d6023a7ffb88"  # From your logs
    
    # These should be two different batch IDs
    batch_1 = "f4086574-c33b-41f5-814c-4cc0c6c52b6d"  # Existing batch from logs
    batch_2 = "00e5e1ab-3c6e-4936-b50d-bc0322ba21d3"  # Target batch from logs
    
    print(f"🧪 Testing batch-specific duplicate validation...")
    print(f"📧 Email: {test_email}")
    print(f"👤 User: {user_id}")
    print(f"📦 Batch 1: {batch_1}")
    print(f"📦 Batch 2: {batch_2}")
    print("-" * 60)
    
    # Test adding to batch 2 (should now work since we fixed batch-specific validation)
    print(f"🎯 Attempting to add {test_email} to batch {batch_2}...")
    
    payload = {
        "email": test_email,
        "name": test_name,
        "phone": test_phone,
        "batch_id": batch_2,
        "user_id": user_id
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/leads/add-single", json=payload)
        
        print(f"📋 Response Status: {response.status_code}")
        print(f"📋 Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Email was added to different batch!")
            return True
        elif response.status_code == 400:
            if "already exists in this batch" in response.text:
                print("✅ EXPECTED: Email already exists in THIS batch (correct behavior)")
                return True
            elif "already exists for this user in batch" in response.text and batch_1 in response.text:
                print("❌ FAILED: Still checking globally across all batches (bug not fixed)")
                return False
            else:
                print(f"⚠️  UNKNOWN 400 ERROR: {response.text}")
                return False
        else:
            print(f"⚠️  UNEXPECTED STATUS: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to backend server. Make sure it's running on port 8000")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_batch_duplicate_validation()
    exit(0 if success else 1)