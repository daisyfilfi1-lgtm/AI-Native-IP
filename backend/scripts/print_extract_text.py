"""Print full extract_text result for a URL (for verification)."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

_BACKEND = Path(__file__).resolve().parents[1]


async def main() -> int:
    load_dotenv(_BACKEND / ".env")
    url = (sys.argv[1] if len(sys.argv) > 1 else "").strip() or "https://v.douyin.com/fxRsYbg9ltI/"
    paste = (sys.argv[2] if len(sys.argv) > 2 else "").strip() or None

    from app.services.text_extractor import extract_text

    r = await extract_text(url, pasted_script=paste)
    print("success:", r.success)
    print("method:", r.method)
    print("error:", r.error or "")
    meta = r.metadata or {}
    keys = (
        "platform",
        "resolved_url",
        "original_url",
        "sub_method",
        "snippet_len",
        "tikhub_len",
        "web_len",
        "asr_len",
        "paste_len",
        "resolve_error",
    )
    slim = {k: meta[k] for k in keys if k in meta}
    print("metadata:", json.dumps(slim, ensure_ascii=False, indent=2))
    print()
    print("===== 提取原文（全文）=====")
    print(r.text or "")
    print("===== 提取原文（结束）=====")
    print("length:", len(r.text or ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
