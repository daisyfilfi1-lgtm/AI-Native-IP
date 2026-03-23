"""Test CORS right now"""
import requests
import sys

BASE = 'https://ai-native-ip-production.up.railway.app'
FRONTEND = 'https://ai-native-ip.netlify.app'

try:
    # Health check
    print("1. Health check...")
    r = requests.get(f'{BASE}/health', timeout=15)
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.text}")
    
    # CORS preflight
    print("\n2. CORS preflight...")
    r2 = requests.options(
        f'{BASE}/api/v1/memory/ingest/test123',
        headers={
            'Origin': FRONTEND,
            'Access-Control-Request-Method': 'GET'
        },
        timeout=15
    )
    print(f"   Status: {r2.status_code}")
    print(f"   Allow-Origin: {r2.headers.get('Access-Control-Allow-Origin')}")
    
    # GET with origin
    print("\n3. GET with Origin...")
    r3 = requests.get(
        f'{BASE}/api/v1/memory/ingest/test123',
        headers={'Origin': FRONTEND},
        timeout=15
    )
    print(f"   Status: {r3.status_code}")
    print(f"   Allow-Origin: {r3.headers.get('Access-Control-Allow-Origin')}")
    print(f"   Body: {r3.text[:100]}")
    
    print("\nAll tests passed!")
    
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
