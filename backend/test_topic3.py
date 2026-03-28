import requests
import json

# Use my new topic recommendation API
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
    
    print(f'\n=== 小敏IP智能选题推荐 (前3个) ===\n')
    for i, item in enumerate(data, 1):
        print(f'选题 {i}: {item["topic"]}')
        print(f'  平台: {item["platform"]}')
        print(f'  综合评分: {item["overall_score"]}')
        print(f'  流量:{item["traffic_score"]} 变现:{item["monetization_score"]} 契合:{item["fit_score"]} 成本:{item["cost_score"]}')
        print(f'  爆款元素: {item["viral_elements"]}')
        print(f'  URL: {item["url"][:60]}...')
        print()
else:
    print(f'Error: {resp.text}')