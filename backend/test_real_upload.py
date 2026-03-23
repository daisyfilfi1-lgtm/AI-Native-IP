"""
Test real upload to production
"""
import requests
import json

API_BASE = 'https://ai-native-ip-production.up.railway.app/api/v1'
FRONTEND = 'https://ai-native-ip.netlify.app'

# Use first IP
IP_ID = '1'

print("Testing REAL upload to IP:", IP_ID)
print()

# Test 1: Upload file
print("1. Uploading test file...")
test_content = b"This is a real test file for upload testing. " * 100  # ~5KB

response = requests.post(
    f"{API_BASE}/memory/upload",
    headers={"Origin": FRONTEND},
    data={"ip_id": IP_ID},
    files={"file": ("test_upload.txt", test_content, "text/plain")},
    timeout=60
)

print(f"   Status: {response.status_code}")
print(f"   CORS: {response.headers.get('Access-Control-Allow-Origin')}")

if response.status_code == 200:
    data = response.json()
    print(f"   File ID: {data.get('file_id')}")
    print(f"   File URL: {data.get('file_url')}")
    file_id = data.get('file_id')
    
    # Test 2: Create ingest task
    print()
    print("2. Creating ingest task...")
    ingest_resp = requests.post(
        f"{API_BASE}/memory/ingest",
        headers={"Origin": FRONTEND, "Content-Type": "application/json"},
        json={
            "ip_id": IP_ID,
            "source_type": "text",
            "local_file_id": file_id,
            "title": "Test upload"
        },
        timeout=30
    )
    
    print(f"   Status: {ingest_resp.status_code}")
    if ingest_resp.status_code == 200:
        task_data = ingest_resp.json()
        print(f"   Task ID: {task_data.get('ingest_task_id')}")
        print(f"   Status: {task_data.get('status')}")
        
        # Test 3: Check task status
        print()
        print("3. Checking task status...")
        task_id = task_data.get('ingest_task_id')
        status_resp = requests.get(
            f"{API_BASE}/memory/ingest/{task_id}",
            headers={"Origin": FRONTEND},
            timeout=30
        )
        
        print(f"   Status: {status_resp.status_code}")
        print(f"   Response: {status_resp.json()}")
        
    else:
        print(f"   Error: {ingest_resp.text}")
        
elif response.status_code == 413:
    print("   ERROR: File too large")
elif response.status_code == 502:
    print("   ERROR: Backend crashed (502)")
else:
    print(f"   Error: {response.text[:500]}")

print()
print("Test complete!")
