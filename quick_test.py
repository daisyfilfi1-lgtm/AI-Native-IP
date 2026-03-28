# -*- coding: utf-8 -*-
import asyncio
import httpx
import re
import json
import sys

async def main():
    url = "https://www.douyin.com/video/7499488512974989568"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        r = await client.get(url, headers=headers)
        
        text = r.text
        match = re.search(r'window\.__UNIVERSAL_DATA__\s*=\s*({.+?});', text)
        
        if match:
            data = json.loads(match.group(1))
            if 'detail' in data:
                detail = data['detail']
                desc = detail.get('desc', '')
                # 写入文件
                with open('douyin_result.txt', 'w', encoding='utf-8') as f:
                    f.write(f"desc: {desc}\n")
                    f.write(f"keys: {list(detail.keys())[:15]}\n")
                print("DONE")
        else:
            print("NOT_FOUND")

asyncio.run(main())
print("Script finished")