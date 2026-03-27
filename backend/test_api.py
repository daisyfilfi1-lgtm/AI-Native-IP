import requests
import json

url = "http://localhost:8000/api/v1/remix/enhanced"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": "dev-key-do-not-use-in-production"
}
data = {
    "ip_id": "xiaomin1",
    "competitor_content": "不是实体难干，也不是实体没希望了，依然有很多实体干的很好，甚至比以前更好。如果你能看完我总结的这四点，相信你一定会豁然开朗",
    "topic": "实体经济",
    "viral_elements": ["contrast", "crowd"],
    "max_iterations": 1
}

resp = requests.post(url, headers=headers, json=data, timeout=180)
print(f"Status: {resp.status_code}")

with open("F:/AI-Native IP/backend/remix_result.json", "w", encoding="utf-8") as f:
    json.dump(resp.json(), f, ensure_ascii=False, indent=2)

print("Saved to remix_result.json")