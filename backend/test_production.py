"""
Production Environment Test Script - Diagnose upload issues

Usage:
    cd backend
    python test_production.py

Tests:
    1. Backend health check
    2. CORS configuration
    3. File upload API
    4. IP list retrieval
"""
import requests
import sys
import json
from datetime import datetime

# Config
FRONTEND_URL = "https://ai-native-ip.netlify.app"
BACKEND_URL = "https://ai-native-ip-production.up.railway.app"
API_BASE = f"{BACKEND_URL}/api/v1"

def print_header(text):
    print(f"\n{'='*60}")
    print(f"{text}")
    print(f"{'='*60}")

def print_success(text):
    print(f"[OK] {text}")

def print_error(text):
    print(f"[ERROR] {text}")

def print_warning(text):
    print(f"[WARN] {text}")

def print_info(text):
    print(f"  {text}")

def test_health():
    """Test backend health"""
    print_header("Test 1: Backend Health Check")
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        if response.status_code == 200:
            print_success("Health check passed")
            print_info(f"Response: {response.json()}")
            return True
        else:
            print_error(f"Health check failed: HTTP {response.status_code}")
            print_info(f"Response: {response.text}")
            return False
    except requests.exceptions.Timeout:
        print_error("Health check timeout (10s)")
        return False
    except Exception as e:
        print_error(f"Health check error: {e}")
        return False

def test_cors_preflight():
    """Test CORS preflight"""
    print_header("Test 2: CORS Preflight Request")
    
    try:
        response = requests.options(
            f"{API_BASE}/memory/upload",
            headers={
                "Origin": FRONTEND_URL,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            },
            timeout=10
        )
        
        print_info(f"Status: {response.status_code}")
        
        # Check CORS headers
        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
            "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
            "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
        }
        
        for header, value in cors_headers.items():
            if value:
                print_success(f"{header}: {value}")
            else:
                print_error(f"Missing {header}")
        
        # Check CORS config
        allow_origin = response.headers.get("Access-Control-Allow-Origin")
        if allow_origin == "*" or FRONTEND_URL in (allow_origin or ""):
            print_success("CORS configured correctly")
            return True
        else:
            print_error(f"CORS issue, allowed origin: {allow_origin}")
            return False
            
    except Exception as e:
        print_error(f"CORS test error: {e}")
        return False

def test_cors_actual():
    """Test actual CORS request"""
    print_header("Test 3: CORS Actual Request")
    
    try:
        # GET request test
        response = requests.get(
            f"{API_BASE}/memory/assets?ip_id=test&limit=1",
            headers={"Origin": FRONTEND_URL},
            timeout=10
        )
        
        print_info(f"GET /memory/assets Status: {response.status_code}")
        print_info(f"Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")
        
        if response.headers.get("Access-Control-Allow-Origin"):
            print_success("CORS headers present")
            return True
        else:
            print_error("Missing CORS headers")
            return False
            
    except Exception as e:
        print_error(f"CORS actual test error: {e}")
        return False

def test_upload():
    """Test upload API"""
    print_header("Test 4: Upload API Test (no valid IP)")
    
    test_content = b"Test file content"
    
    try:
        response = requests.post(
            f"{API_BASE}/memory/upload",
            headers={"Origin": FRONTEND_URL},
            data={"ip_id": "non_existent_ip_12345"},
            files={"file": ("test.txt", test_content, "text/plain")},
            timeout=30
        )
        
        print_info(f"Status: {response.status_code}")
        print_info(f"Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")
        
        if response.status_code == 404:
            print_success("Upload API responding (404 is expected - IP not found)")
            return True
        elif response.status_code == 200:
            print_success("Upload successful")
            return True
        elif response.status_code == 502:
            print_error("Backend 502 error - app crashed")
            return False
        else:
            print_warning(f"Unexpected status: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print_error("Upload timeout (30s)")
        return False
    except Exception as e:
        print_error(f"Upload test error: {e}")
        return False

def test_list_ips():
    """Test IP list"""
    print_header("Test 5: IP List")
    
    try:
        response = requests.get(
            f"{API_BASE}/ip",
            headers={"Origin": FRONTEND_URL},
            timeout=10
        )
        
        print_info(f"Status: {response.status_code}")
        print_info(f"Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Got {len(data)} IPs")
            return True
        else:
            print_error(f"Failed: {response.text[:200]}")
            return False
            
    except Exception as e:
        print_error(f"IP list error: {e}")
        return False

def main():
    print(f"\nAI-Native IP Production Test")
    print(f"Frontend: {FRONTEND_URL}")
    print(f"Backend: {BACKEND_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    
    results = []
    
    results.append(("Health Check", test_health()))
    results.append(("CORS Preflight", test_cors_preflight()))
    results.append(("CORS Actual", test_cors_actual()))
    results.append(("Upload API", test_upload()))
    results.append(("IP List", test_list_ips()))
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"  {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print_success("All tests passed!")
        return 0
    else:
        print_error("Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
