import requests
import json

resp = requests.get(
    'http://localhost:8000/api/v1/strategy/topics/recommend',
    params={'ip_id': 'xiaomin1', 'limit': 3},
    headers={'X-API-Key': 'dev-key-do-not-use-in-production'},
    timeout=60
)
print(f'Status: {resp.status_code}')

if resp.status_code == 200:
    data = resp.json()
    with open('F:/AI-Native IP/backend/topic_result_new.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f'OK - Saved {len(data)} topics')
    for i, item in enumerate(data, 1):
        print(f'{i}. {item["topic"]}')
        print(f'   Score: {item["overall_score"]}')
else:
    print(f'Error: {resp.text}')