import requests
import json

url = "http://localhost:8000/api/v1/strategy/topics/recommend"
headers = {
    "X-API-Key": "dev-key-do-not-use-in-production"
}
params = {
    "ip_id": "xiaomin1",
    "limit": 3
}

resp = requests.get(url, headers=headers, params=params, timeout=60)
print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    data = resp.json()
    with open("F:/AI-Native IP/backend/topic_result.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Saved to topic_result.json")
    
    # Print summary
    for i, item in enumerate(data, 1):
        print(f"\n=== 选题 {i} ===")
        print(f"标题: {item['topic']}")
        print(f"平台: {item['platform']}")
        print(f"综合评分: {item['overall_score']}")
        print(f"流量: {item['traffic_score']} | 变现: {item['monetization_score']} | IP契合: {item['fit_score']} | 成本: {item['cost_score']}")
        print(f"爆款元素: {item['viral_elements']}")
else:
    print(f"Error: {resp.text}")