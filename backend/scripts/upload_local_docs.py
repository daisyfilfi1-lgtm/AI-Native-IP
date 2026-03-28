"""
Local file batch upload script
Upload docs from local folder to system
"""
import os
import requests
import glob

API_URL = "https://ai-native-ip-production.up.railway.app"
IP_ID = "1"
SUPPORTED_EXTENSIONS = ['.txt', '.md', '.doc', '.docx', '.pdf']
DOCS_DIR = r"F:\AI-Native IP\docs\IP知识库"

def get_files():
    files = []
    for ext in SUPPORTED_EXTENSIONS:
        pattern = os.path.join(DOCS_DIR, f"*{ext}")
        files.extend(glob.glob(pattern))
    return files

def upload_file(file_path):
    filename = os.path.basename(file_path)
    print(f"Uploading: {filename}")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f, 'application/octet-stream')}
            data = {'ip_id': IP_ID}
            response = requests.post(f"{API_URL}/api/v1/memory/upload", files=files, data=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                print(f"  OK: {result.get('file_id', '')}")
                return True
            else:
                print(f"  FAIL: {response.status_code}")
                return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

files = get_files()
print(f"Found {len(files)} files")

success = 0
failed = 0
for f in files:
    if upload_file(f):
        success += 1
    else:
        failed += 1

print(f"Done! Success: {success}, Failed: {failed}")
