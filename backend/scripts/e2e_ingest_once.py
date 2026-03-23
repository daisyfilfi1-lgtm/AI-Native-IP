"""一次上传 + 录入 + 轮询状态（用于验证生产录入链路）。"""
import json
import os
import sys
import time

import requests

API = os.environ.get(
    "E2E_API_BASE", "https://ai-native-ip-production.up.railway.app/api/v1"
)
ORIGIN = os.environ.get("E2E_ORIGIN", "https://ai-native-ip.netlify.app")
IP_ID = os.environ.get("E2E_IP_ID", "1")


def main() -> int:
    content = (b"e2e line\n") * 400
    r = requests.post(
        f"{API}/memory/upload",
        headers={"Origin": ORIGIN},
        data={"ip_id": IP_ID},
        files={"file": ("e2e_once.txt", content, "text/plain")},
        timeout=90,
    )
    print("upload", r.status_code, r.text[:300])
    r.raise_for_status()
    file_id = r.json()["file_id"]

    r2 = requests.post(
        f"{API}/memory/ingest",
        headers={"Origin": ORIGIN, "Content-Type": "application/json"},
        json={
            "ip_id": IP_ID,
            "source_type": "text",
            "local_file_id": file_id,
            "title": "e2e_once",
        },
        timeout=40,
    )
    print("ingest", r2.status_code, r2.text[:300])
    r2.raise_for_status()
    task_id = r2.json()["ingest_task_id"]
    print("task_id", task_id)

    for i in range(120):
        d = requests.get(f"{API}/memory/ingest/{task_id}", timeout=25).json()
        st = d.get("status")
        err = (d.get("error") or "")[:120]
        n = len(d.get("created_assets") or [])
        print(f"{i:3d} {st} assets={n} err={err!r}")
        if st in ("COMPLETED", "FAILED"):
            print("FINAL", json.dumps(d, ensure_ascii=False))
            return 0 if st == "COMPLETED" else 1
        time.sleep(2)

    print("TIMEOUT polling")
    return 2


if __name__ == "__main__":
    sys.exit(main())
