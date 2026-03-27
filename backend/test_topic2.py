import requests
import json

# Use existing creator topics API
resp = requests.get(
    'http://localhost:8000/api/creator/topics/recommended',
    params={'ip_id': 'xiaomin1'},
    headers={'X-API-Key': 'dev-key-do-not-use-in-production'},
    timeout=30
)
print(f'Status: {resp.status_code}')

data = resp.json()
with open('F:/AI-Native IP/backend/topic_result.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'Total topics: {len(data)}')
for i, item in enumerate(data[:3], 1):
    title = item.get('title', item.get('topic', 'N/A'))
    print(f'{i}. {title[:60]}')
    if 'score' in item:
        print(f'   Score: {item["score"]}')