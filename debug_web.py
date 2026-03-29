# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

"""从抖音PC页面提取内容"""
import asyncio
import os
import sys
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

import httpx

PC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

async def extract_douyin_content():
    url = "https://www.douyin.com/video/7499488512974989568"
    
    print(f"请求: {url}")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=10.0), follow_redirects=True) as client:
        r = await client.get(url, headers=PC_HEADERS)
        print(f"状态: {r.status_code}")
        
        html = r.text
        
        # 方法1: 从 <title> 提取
        title_match = re.search(r'<title>([^<]+)</title>', html)
        if title_match:
            title = title_match.group(1).strip()
            print(f"\n方法1 - Title: {title}")
        
        # 方法2: 从 meta 提取
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
        if desc_match:
            desc = desc_match.group(1).strip()
            print(f"方法2 - Meta desc: {desc[:100]}...")
        
        og_title_match = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
        if og_title_match:
            og_title = og_title_match.group(1).strip()
            print(f"方法3 - OG title: {og_title}")
        
        # 方法4: 从 JSON 数据提取
        # 抖音页面通常包含 __UNIVERSAL_DATA__ 或 __INITIAL_STATE__ 
        json_patterns = [
            r'window\.__UNIVERSAL_DATA__\s*=\s*({.+?});',
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'window\.__DATA__\s*=\s*({.+?});',
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, html)
            if match:
                print(f"\n找到JSON数据: {pattern[:30]}...")
                import json
                try:
                    data = json.loads(match.group(1))
                    print(f"JSON keys: {list(data.keys())[:5]}")
                    
                    # 尝试找 desc
                    def find_desc(obj, depth=0):
                        if depth > 4:
                            return None
                        if isinstance(obj, dict):
                            for k in ['desc', 'title', 'content', 'text', 'share_title']:
                                if k in obj and obj[k]:
                                    return obj[k]
                            for v in obj.values():
                                if isinstance(v, (dict, list)):
                                    result = find_desc(v, depth+1)
                                    if result:
                                        return result
                        elif isinstance(obj, list) and obj:
                            return find_desc(obj[0], depth+1)
                        return None
                    
                    desc = find_desc(data)
                    if desc:
                        print(f"方法4 - JSON desc: {desc[:100]}...")
                except Exception as e:
                    print(f"JSON解析失败: {e}")
                break

if __name__ == "__main__":
    asyncio.run(extract_douyin_content())