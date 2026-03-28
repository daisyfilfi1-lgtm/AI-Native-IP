"""
文本提取服务测试脚本
用于验证新架构的各项功能
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_link_resolver():
    """测试链接解析器"""
    print("\n" + "="*60)
    print("测试1: 链接解析器")
    print("="*60)
    
    from app.services.link_resolver import detect_platform, extract_video_id
    
    test_urls = [
        ("https://v.douyin.com/xxxxx", "douyin"),
        ("https://www.douyin.com/video/123456", "douyin"),
        ("https://xhslink.com/xxxxx", "xiaohongshu"),
        ("https://www.xiaohongshu.com/explore/123", "xiaohongshu"),
        ("https://v.kuaishou.com/xxxxx", "kuaishou"),
        ("https://b23.tv/xxxxx", "bilibili"),
        ("https://www.bilibili.com/video/BV1xx411c7mD", "bilibili"),
    ]
    
    for url, expected in test_urls:
        platform = detect_platform(url)
        video_id = extract_video_id(url, platform)
        status = "✓" if platform == expected else "✗"
        print(f"  {status} {url[:40]}...")
        print(f"     平台: {platform} (期望: {expected})")
        print(f"     视频ID: {video_id}")


async def test_text_extractor_interface():
    """测试提取服务接口"""
    print("\n" + "="*60)
    print("测试2: 提取服务接口")
    print("="*60)
    
    from app.services.text_extractor import ExtractResult
    
    # 测试成功结果
    result = ExtractResult(
        success=True,
        text="测试文本",
        method="test",
        metadata={"key": "value"}
    )
    print(f"  ✓ ExtractResult 创建成功")
    print(f"    success: {result.success}")
    print(f"    text length: {len(result.text)}")
    print(f"    method: {result.method}")
    print(f"    metadata: {result.metadata}")
    
    # 测试失败结果
    result = ExtractResult(
        success=False,
        text="",
        method="none",
        error="测试错误"
    )
    print(f"  ✓ 失败结果创建成功")
    print(f"    error: {result.error}")


async def test_extraction_flow():
    """测试完整提取流程"""
    print("\n" + "="*60)
    print("测试3: 完整提取流程")
    print("="*60)
    
    from app.services.competitor_text_extraction import extract_competitor_text_with_fallback
    
    # 测试空链接
    result = await extract_competitor_text_with_fallback("")
    print(f"  ✓ 空链接处理: success={result['success']}, error={result['error'][:30]}")
    
    # 测试无效链接（应该走兜底）
    result = await extract_competitor_text_with_fallback("not_a_url")
    print(f"  ✓ 无效链接处理: success={result['success']}, method={result['method']}")


async def test_platform_detection():
    """测试平台检测"""
    print("\n" + "="*60)
    print("测试4: 平台检测")
    print("="*60)
    
    from app.services.link_resolver import PLATFORM_PATTERNS, detect_platform
    
    print(f"  支持的平台: {list(PLATFORM_PATTERNS.keys())}")
    
    # 测试未知平台
    platform = detect_platform("https://unknown.com/video/123")
    print(f"  ✓ 未知平台检测: {platform}")


def print_architecture():
    """打印架构图"""
    print("""
═══════════════════════════════════════════════════════════════
文本提取服务架构
═══════════════════════════════════════════════════════════════

用户输入链接
    ↓
┌─────────────────────────────────────────┐
│  link_resolver.py                        │
│  • 短链解析                              │
│  • 平台识别                              │
│  • 视频ID提取                            │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  text_extractor.py                       │
│  • TikHub API 提取                       │
│  • Web 爬取提取                          │
│  • yt-dlp 提取                           │
└─────────────────────────────────────────┘
    ↓
返回 ExtractResult

═══════════════════════════════════════════════════════════════
""")


async def main():
    """运行所有测试"""
    print_architecture()
    
    try:
        await test_link_resolver()
    except Exception as e:
        print(f"  ✗ 链接解析器测试失败: {e}")
    
    try:
        await test_text_extractor_interface()
    except Exception as e:
        print(f"  ✗ 提取服务接口测试失败: {e}")
    
    try:
        await test_extraction_flow()
    except Exception as e:
        print(f"  ✗ 提取流程测试失败: {e}")
    
    try:
        await test_platform_detection()
    except Exception as e:
        print(f"  ✗ 平台检测测试失败: {e}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
