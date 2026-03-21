import os, requests, glob, json

API = "https://ai-native-ip-production.up.railway.app"
IP = "1"
DIR = r"F:\AI-Native IP\docs\IP知识库"

out = []
out.append("Starting...")

files = []
for ext in ['.txt','.md','.doc','.docx','.pdf']:
    files.extend(glob.glob(os.path.join(DIR, f"*{ext}")))

out.append(f"Found {len(files)} files")

results = []
for f in files:
    name = os.path.basename(f)
    try:
        with open(f, 'rb') as fp:
            r = requests.post(f"{API}/api/v1/memory/upload", files={'file': (name, fp)}, data={'ip_id': IP}, timeout=60)
            if r.status_code == 200:
                results.append(f"OK: {name}")
            else:
                results.append(f"FAIL: {name} - {r.status_code}")
    except Exception as e:
        results.append(f"ERROR: {name} - {str(e)[:50]}")

out.extend(results)
out.append(f"Done! {len([x for x in results if x.startswith('OK')])} success")

with open('F:/temp/upload_result.txt', 'w', encoding='utf-8') as fp:
    fp.write('\n'.join(out))
