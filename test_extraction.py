# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

"""测试统一文本提取服务"""
import asyncio
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.chdir(os.path.join(os.path.dirname(__file__), "backend"))

os.environ["TIKHUB_API_KEY"] = "qJkdBOoQ3w6H3SvWWN+e4QXUJhHSX4Z97SLWqEDbWce+jHeTeFDSbCigDQ=="

from app.services.text_extractor import extract_text

async def test_extraction():
    test_cases = [
        ("抖音视频页", "https://www.douyin.com/video/7499488512974989568"),
        ("小红书有效链接", "https://www.xiaohongshu.com/explore/67b8c4a2000000001d00f32e"),
    ]
    
    for name, url in test_cases:
        print(f"\n{'='*60}")
        print(f"测试 {name}: {url[:50]}...")
        print("="*60)
        
        result = await extract_text(url)
        print(f"\n成功: {result.success}")
        print(f"方法: {result.method}")
        print(f"长度: {len(result.text)}")
        print(f"错误: {result.error}")
        if result.text:
            print(f"预览: {result.text[:200]}...")

if __name__ == "__main__":
    print("=== 测试统一提取服务 ===")
    asyncio.run(test_extraction())
    print("\n=== 完成 ===")