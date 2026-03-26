# -*- coding: utf-8 -*-
"""验证小红书话题 page_id：调用 TikHub get_topic_info。需环境变量 TIKHUB_API_KEY。"""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import tikhub_client


async def main() -> None:
    if len(sys.argv) < 2:
        print("用法: py -3 scripts/tikhub_try_topic_info.py <page_id> [page_id ...]", file=sys.stderr)
        sys.exit(2)
    if not tikhub_client.is_configured():
        print("未设置 TIKHUB_API_KEY", file=sys.stderr)
        sys.exit(1)
    for pid in sys.argv[1:]:
        pid = pid.strip()
        if not pid:
            continue
        try:
            raw = await tikhub_client.fetch_xhs_topic_info(pid)
            name = tikhub_client.topic_display_name_from_xhs_info(raw) or "(无名称)"
            print(f"OK  {pid}  ->  {name}")
            print(json.dumps(raw, ensure_ascii=False, indent=2)[:2000])
        except Exception as e:
            print(f"ERR {pid}  ->  {e}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
