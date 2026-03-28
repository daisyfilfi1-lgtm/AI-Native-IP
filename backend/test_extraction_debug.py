"""
文本提取调试脚本
用于诊断提取失败的具体原因
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_link_resolution():
    """测试链接解析"""
    print("\n" + "="*60)
    print("测试1: 链接解析")
    print("="*60)
    
    from app.services.link_resolver import resolve_any_url
    
    test_url = "http://xhslink.com/o/AnFzdqpp3M7"  # 用户提供的链接
    
    try:
        result = await resolve_any_url(test_url)
        print(f"✓ 链接解析成功")
        print(f"  原始URL: {result['original_url']}")
        print(f"  解析后URL: {result['resolved_url']}")
        print(f"  平台: {result['platform']}")
        print(f"  视频ID: {result['video_id']}")
        print(f"  错误: {result['error']}")
    except Exception as e:
        print(f"✗ 链接解析失败: {e}")
        import traceback
        traceback.print_exc()


async def test_text_extraction():
    """测试完整提取流程"""
    print("\n" + "="*60)
    print("测试2: 完整提取流程")
    print("="*60)
    
    from app.services.text_extractor import extract_text
    
    test_url = "http://xhslink.com/o/AnFzdqpp3M7"
    
    try:
        result = await extract_text(test_url)
        print(f"✓ 提取完成")
        print(f"  成功: {result.success}")
        print(f"  方法: {result.method}")
        print(f"  文本长度: {len(result.text)}")
        print(f"  错误: {result.error[:200] if result.error else '无'}")
        print(f"  元数据: {result.metadata}")
        
        if result.text:
            print(f"\n  文本预览:")
            print(f"  {result.text[:200]}...")
    except Exception as e:
        print(f"✗ 提取异常: {e}")
        import traceback
        traceback.print_exc()


async def test_web_scrape_only():
    """单独测试Web爬取"""
    print("\n" + "="*60)
    print("测试3: Web爬取（小红书）")
    print("="*60)
    
    from app.services.text_extractor import extract_with_web_scrape
    
    test_url = "http://xhslink.com/o/AnFzdqpp3M7"
    
    try:
        result = await extract_with_web_scrape(test_url, "xiaohongshu")
        print(f"✓ Web爬取完成")
        print(f"  成功: {result.success}")
        print(f"  文本长度: {len(result.text)}")
        print(f"  错误: {result.error[:200] if result.error else '无'}")
        
        if result.text:
            print(f"\n  文本预览:")
            print(f"  {result.text[:200]}...")
    except Exception as e:
        print(f"✗ Web爬取异常: {e}")
        import traceback
        traceback.print_exc()


async def test_tikhub_config():
    """测试TikHub配置"""
    print("\n" + "="*60)
    print("测试4: TikHub配置")
    print("="*60)
    
    from app.services import tikhub_client
    
    is_configured = tikhub_client.is_configured()
    print(f"  TikHub已配置: {is_configured}")
    
    if is_configured:
        print(f"  API Key: {os.environ.get('TIKHUB_API_KEY', '未设置')[:10]}...")
    else:
        print(f"  注意: TikHub未配置，将使用Web爬取")


def check_file_exists():
    """检查关键文件是否存在"""
    print("\n" + "="*60)
    print("测试5: 文件检查")
    print("="*60)
    
    files = [
        "app/services/link_resolver.py",
        "app/services/text_extractor.py",
        "app/services/competitor_text_extraction.py",
    ]
    
    for file in files:
        path = os.path.join(os.path.dirname(__file__), file)
        exists = os.path.exists(path)
        size = os.path.getsize(path) if exists else 0
        status = "✓" if exists else "✗"
        print(f"  {status} {file} ({size} bytes)")


async def main():
    print("="*60)
    print("文本提取调试脚本")
    print("="*60)
    
    check_file_exists()
    await test_tikhub_config()
    await test_link_resolution()
    await test_web_scrape_only()
    await test_text_extraction()
    
    print("\n" + "="*60)
    print("调试完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
