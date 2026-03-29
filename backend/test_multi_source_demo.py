"""
多源热榜聚合演示脚本

演示环节1改造后的效果：
1. 多源热榜聚合（抖音+小红书+快手+B站）
2. 内置爆款库兜底
3. 智能IP匹配
"""

import asyncio
import sys
sys.path.insert(0, '.')

from app.services.datasource.multi_source_hotlist import (
    get_multi_source_aggregator,
    fetch_hotlist_fallback,
)
from app.services.datasource.builtin_viral_repository import get_builtin_repository
from app.services.smart_ip_matcher import get_smart_matcher


async def demo_multi_source():
    """演示多源热榜功能"""
    print("=" * 60)
    print("演示：多源热榜聚合")
    print("=" * 60)
    
    # 1. 演示多源聚合
    aggregator = get_multi_source_aggregator()
    
    print("\n1. 获取多平台热榜数据...")
    result = await aggregator.fetch_all(limit_per_platform=5)
    
    print(f"   - 总条目数: {len(result.items)}")
    print(f"   - 来源分布: {result.source_stats}")
    print(f"   - 错误信息: {result.errors}")
    
    # 显示各平台的热榜
    from app.services.datasource.multi_source_hotlist import PlatformType
    for platform in PlatformType:
        platform_items = [i for i in result.items if i.platform == platform]
        if platform_items:
            print(f"\n   [{platform.value.upper()}] 热榜 Top 3:")
            for item in platform_items[:3]:
                print(f"      - {item.title[:40]}... (热度: {item.hot_score:.1f})")
    
    return result


async def demo_builtin_repository():
    """演示内置爆款库"""
    print("\n" + "=" * 60)
    print("演示：内置爆款库")
    print("=" * 60)
    
    repo = get_builtin_repository()
    
    # 测试不同的IP画像
    test_profiles = [
        {
            "name": "宝妈创业IP",
            "expertise": "宝妈创业、副业变现、在家赚钱",
            "content_direction": "女性成长、经济独立",
            "target_audience": "宝妈、想赚钱的女性",
        },
        {
            "name": "知识付费IP",
            "expertise": "知识变现、课程制作、个人品牌",
            "content_direction": "知识付费、内容创业",
            "target_audience": "知识工作者、专业人士",
        },
        {
            "name": "通用型IP",
            "expertise": "个人成长、职场发展",
            "content_direction": "自我提升",
            "target_audience": "年轻人、职场人",
        },
    ]
    
    for profile in test_profiles:
        print(f"\n2. IP画像: {profile['name']}")
        
        # 检测IP类型
        ip_types = repo.detect_ip_type(profile)
        print(f"   - 检测到的类型: {[t.value for t in ip_types]}")
        
        # 获取推荐选题
        topics = repo.get_topics_for_ip(profile, limit=5)
        print(f"   - 推荐选题:")
        for i, topic in enumerate(topics[:3], 1):
            print(f"      {i}. {topic.title}")
            print(f"         类型: {topic.extra.get('content_type')} | 标签: {topic.tags[:3]}")


async def demo_smart_matcher():
    """演示智能IP匹配"""
    print("\n" + "=" * 60)
    print("演示：智能IP匹配")
    print("=" * 60)
    
    matcher = get_smart_matcher()
    
    ip_profile = {
        "name": "宝妈创业导师",
        "expertise": "宝妈创业、副业变现、在家赚钱",
        "content_direction": "女性成长、经济独立",
        "target_audience": "宝妈、想赚钱的女性",
        "unique_value_prop": "帮助宝妈在家实现月入过万",
        "style_features": "亲切、接地气、励志",
    }
    
    test_titles = [
        "从0到月入3万：这个宝妈的副业方法太绝了",  # 高度匹配
        "35岁被裁后，我靠这个月入5万：宝妈逆袭实录",  # 高度匹配
        "Python编程入门教程",  # 不匹配
        "2024年最新手机评测",  # 不匹配
        "每天2小时，月入5位数：打工人必看的副业指南",  # 部分匹配
    ]
    
    print(f"\n3. IP画像: {ip_profile['name']}")
    print(f"   - 领域: {ip_profile['expertise']}")
    print(f"   - 受众: {ip_profile['target_audience']}")
    
    print(f"\n   - 标题匹配度分析:")
    for title in test_titles:
        match_result = matcher.analyze_match(title, ip_profile)
        content_type, confidence = matcher.detect_content_type(title)
        viral_elements = matcher.extract_viral_elements(title)
        
        print(f"\n     标题: {title[:40]}")
        print(f"     - 匹配分数: {match_result.overall:.2f}")
        print(f"     - 内容类型: {content_type} (置信度: {confidence:.2f})")
        print(f"     - 爆款元素: {viral_elements}")
        print(f"     - 各维度得分: {match_result.dimensions}")


async def demo_integrated_flow():
    """演示完整流程：多源+内置库+IP匹配"""
    print("\n" + "=" * 60)
    print("演示：完整链路（多源+内置库+IP匹配）")
    print("=" * 60)
    
    ip_profile = {
        "name": "宝妈创业导师",
        "expertise": "宝妈创业、副业变现、在家赚钱",
        "content_direction": "女性成长、经济独立",
        "target_audience": "宝妈、想赚钱的女性",
    }
    
    print(f"\n4. 为IP '{ip_profile['name']}' 获取推荐选题...")
    
    # 使用新的fetch_hotlist_fallback函数
    topics = await fetch_hotlist_fallback(ip_profile, limit=10)
    
    print(f"   - 获取到 {len(topics)} 条选题")
    print(f"\n   - 推荐结果:")
    
    # 分析每条选题的匹配度
    matcher = get_smart_matcher()
    for i, topic in enumerate(topics[:5], 1):
        match_score = matcher.calculate_match_score(topic.title, ip_profile)
        source = "内置库" if topic.extra.get("is_builtin") else "多源热榜"
        
        print(f"\n     {i}. [{source}] 匹配度: {match_score:.2f}")
        print(f"        {topic.title}")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("环节1改造演示：API搜爆款链接")
    print("=" * 60)
    print("\n新特性：")
    print("1. 多源热榜聚合（抖音+小红书+快手+B站）")
    print("2. 内置爆款库兜底（60+高质量模板）")
    print("3. 智能IP匹配（语义级分析）")
    
    try:
        # 运行各个演示
        await demo_multi_source()
        await demo_builtin_repository()
        await demo_smart_matcher()
        await demo_integrated_flow()
        
        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)
        print("\n改造亮点：")
        print("✓ 多平台热榜聚合，数据源更丰富")
        print("✓ API失败时自动使用内置库兜底")
        print("✓ 基于IP画像智能筛选和排序")
        print("✓ 语义级匹配，不只是关键词")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
