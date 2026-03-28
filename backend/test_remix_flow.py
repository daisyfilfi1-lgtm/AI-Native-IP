"""
仿写流程端到端测试脚本
测试从链接输入到生成结果的完整链路
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.competitor_text_extraction import extract_competitor_text_for_remix, resolve_short_url
from app.services import tikhub_client


async def test_url_resolution():
    """测试短链解析"""
    print("\n=== 测试1: 短链解析 ===")
    test_urls = [
        "https://v.douyin.com/xxxxx",  # 抖音短链（示例，可能失效）
        "https://www.douyin.com/video/123456",  # 抖音长链
        "https://xhslink.com/xxxxx",  # 小红书短链
    ]
    
    for url in test_urls:
        try:
            resolved = await resolve_short_url(url)
            print(f"  {url[:40]}... -> {resolved[:50]}...")
        except Exception as e:
            print(f"  {url[:40]}... -> 错误: {e}")


async def test_tikhub_config():
    """测试TikHub配置状态"""
    print("\n=== 测试2: TikHub配置状态 ===")
    configured = tikhub_client.is_configured()
    print(f"  TikHub已配置: {configured}")
    if configured:
        print(f"  API Key: {os.environ.get('TIKHUB_API_KEY', '')[:10]}...")
    else:
        print("  警告: TIKHUB_API_KEY 未配置，仿写功能将使用兜底方案")


async def test_text_extraction():
    """测试文本提取（使用示例链接）"""
    print("\n=== 测试3: 竞品文本提取 ===")
    
    # 使用一个公开的抖音视频链接测试（可能需要替换为有效链接）
    test_url = "https://www.douyin.com"  # 简化测试
    
    try:
        text = await extract_competitor_text_for_remix(test_url)
        print(f"  输入URL: {test_url}")
        print(f"  提取文本长度: {len(text)}")
        print(f"  提取文本预览: {text[:200]}...")
        
        if not text or len(text) < 10:
            print("  ⚠️ 警告: 提取的文本过短，可能影响仿写质量")
    except Exception as e:
        print(f"  错误: {e}")


async def test_scenario_two_pipeline():
    """测试场景二生成管道"""
    print("\n=== 测试4: 场景二生成管道 ===")
    
    from app.services.content_scenario import ScenarioTwoGenerator
    
    # 模拟IP画像
    ip_profile = {
        "ip_id": "xiaomin1",
        "name": "小敏",
        "self_name": "小敏",
        "expertise": "宝妈创业、花样馒头",
        "content_direction": "女性独立、搞钱方法论",
        "target_audience": "想搞钱的宝妈",
    }
    
    # 模拟竞品内容（如果文本提取失败，这就是兜底文本）
    competitor_content = """
    30岁被裁员后，我用这个方法月入5万
    你是不是也在为钱发愁？每天上班累死累活，工资却不见涨？
    我曾经也是这样，直到我发现了这个副业方法...
    现在我把这个方法分享给你，记得点赞收藏！
    """
    
    generator = ScenarioTwoGenerator(ip_profile)
    
    try:
        result = await generator.generate(
            competitor_content=competitor_content,
            platform="douyin",
            rewrite_level="medium"
        )
        print(f"  生成状态: {'成功' if result.content else '失败'}")
        print(f"  内容长度: {len(result.content)}")
        print(f"  质量评分: {result.score}")
        print(f"  元数据: {result.metadata.keys()}")
        
        if not result.content:
            print("  ⚠️ 警告: 生成内容为空")
    except Exception as e:
        print(f"  错误: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("仿写流程诊断测试")
    print("=" * 60)
    
    await test_url_resolution()
    await test_tikhub_config()
    await test_text_extraction()
    await test_scenario_two_pipeline()
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
