"""
One-off: POST /api/v1/creator/generate/remix and poll /status until done or timeout.
Usage (from repo root): py backend/scripts/test_remix_link.py [URL]
Requires API_KEY in backend/.env matching production Railway when testing production.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx

_BACKEND = Path(__file__).resolve().parents[1]


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(_BACKEND / ".env")

    base = os.environ.get("TEST_API_ORIGIN", "https://ai-native-ip-production.up.railway.app").rstrip("/")
    key = os.environ.get("API_KEY", "").strip()
    test_url = (sys.argv[1] if len(sys.argv) > 1 else "").strip() or "http://xhslink.com/o/2BJE4jxulSP"

    is_local = "127.0.0.1" in base or "localhost" in base
    if not key and not is_local:
        print("ERROR: API_KEY missing in backend/.env — cannot call production API.")
        print("       Or set TEST_API_ORIGIN=http://127.0.0.1:8000 and run backend locally.")
        return 2

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if key:
        headers["X-API-Key"] = key
    body = {"url": test_url, "style": "angry", "ipId": "xiaomin1"}

    remix_path = "/api/v1/creator/generate/remix"
    print(f"POST {base}{remix_path} …")

    with httpx.Client(timeout=120.0) as client:
        r = client.post(f"{base}{remix_path}", json=body, headers=headers)
        if r.status_code != 200:
            print(f"POST failed: HTTP {r.status_code}")
            print(r.text[:800])
            return 1
        submit = r.json()
        task_id = submit.get("task_id")
        if not task_id:
            print("No task_id:", json.dumps(submit, ensure_ascii=False)[:500])
            return 1
        print(f"task_id={task_id}")

        status_path = f"/api/v1/creator/generate/remix/{task_id}/status"
        deadline = time.time() + 600
        while time.time() < deadline:
            time.sleep(2)
            sr = client.get(f"{base}{status_path}", headers=headers)
            if sr.status_code != 200:
                print(f"status HTTP {sr.status_code}: {sr.text[:400]}")
                return 1
            st = sr.json()
            s, prog, stage = st.get("status"), st.get("progress"), st.get("stage")
            print(f"  status={s} progress={prog} stage={stage}")
            if s == "completed":
                print("OK: remix task completed.")
                return 0
            if s == "failed":
                err = st.get("error") or st
                print("FAILED:", err)
                return 1

        print("TIMEOUT: still processing after 600s")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
