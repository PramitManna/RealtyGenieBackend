#!/usr/bin/env python3
"""
RealtyGenie Backend Deployment Test Script
Run this after deployment to verify all endpoints work correctly.
"""

import requests
import json
import sys
from datetime import datetime

def test_endpoint(base_url, endpoint, method="GET", data=None, expected_status=200):
    """Test a single API endpoint."""
    url = f"{base_url}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=data, headers=headers, timeout=30)
        
        print(f"  {method} {endpoint}: ", end="")
        
        if response.status_code == expected_status:
            print(f"✅ {response.status_code}")
            return True, response.json() if response.content else None
        else:
            print(f"❌ {response.status_code} - {response.text[:100]}...")
            return False, None
            
    except requests.exceptions.Timeout:
        print(f"❌ Timeout after 30 seconds")
        return False, None
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
        return False, None
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False, None

def main():
    """Run deployment tests."""
    if len(sys.argv) < 2:
        print("Usage: python test_deployment.py <base_url>")
        print("Example: python test_deployment.py https://your-app.onrender.com")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip('/')
    print(f"🧪 Testing RealtyGenie Backend deployment at: {base_url}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Health Check
    print("1️⃣  Testing Health Endpoint")
    tests_total += 1
    success, data = test_endpoint(base_url, "/api/health")
    if success and data and data.get("status") == "healthy":
        tests_passed += 1
        print(f"    Service: {data.get('service')}")
        print(f"    Timestamp: {data.get('timestamp')}")
    
    # Test 2: Root Documentation
    print("\\n2️⃣  Testing Root Documentation") 
    tests_total += 1
    success, data = test_endpoint(base_url, "/api/")
    if success:
        tests_passed += 1
    
    # Test 3: API Documentation (Swagger)
    print("\\n3️⃣  Testing API Documentation")
    tests_total += 1
    success, _ = test_endpoint(base_url, "/docs", expected_status=200)
    if success:
        tests_passed += 1
    
    # Test 4: Trigger Email Endpoint (should fail without auth - that's expected)
    print("\\n4️⃣  Testing Trigger Email Endpoint (validation)")
    tests_total += 1
    test_data = {
        "batch_ids": ["test-batch"],
        "purpose": "test",
        "tones": ["professional"]
        # Missing user_id intentionally
    }
    success, _ = test_endpoint(base_url, "/api/lead-nurture/trigger-email", 
                             method="POST", data=test_data, expected_status=422)
    if success:
        tests_passed += 1
        print("    ✅ Validation working correctly (missing user_id)")
    
    # Test 5: CORS Headers  
    print("\\n5️⃣  Testing CORS Configuration")
    tests_total += 1
    try:
        response = requests.options(f"{base_url}/api/health", timeout=10)
        if "access-control-allow-origin" in response.headers:
            tests_passed += 1
            print("  ✅ CORS headers present")
        else:
            print("  ❌ CORS headers missing")
    except Exception as e:
        print(f"  ❌ CORS test failed: {str(e)}")
    
    # Results Summary
    print("\\n" + "=" * 60)
    print(f"🎯 Test Results: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("🎉 All tests passed! Deployment is successful.")
        print("\\n📋 Ready for production use:")
        print(f"   • API Base URL: {base_url}/api")
        print(f"   • Health Check: {base_url}/api/health")
        print(f"   • Documentation: {base_url}/docs")
        print(f"   • Interactive API: {base_url}/redoc")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit(main())