#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整数据源测试脚本
测试所有已集成的数据源
"""

import asyncio
import json
import sys
import io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, "f:\\AI-Native IP\\backend")

from app.services.datasource import get_datasource_manager_v2
from app.services.datasource.free_sources import (
    DailyHotDataSource,
    VVhanDataSource,
    WeiboHotDataSource,
    DouyinHotDataSource,
)
from app.services.datasource.paid_sources import (
    ShunWeiDataSource,
    QQLYKMDataSource,
    TopHubDataSource,
)
from app.services.datasource.platform_sources import (
    XiaohongshuDataSource,
    DouyinDataSource,
    WeiboDataSource,
)

TEST_IP_PROFILE = {
    "ip_id": "xiaomin1",
    "name": "馒头女子",
    "expertise": "花样馒头制作/私域运营/短视频获客",
    "content_direction": "花样馒头创业/女性独立/私域变现",
}


def print_separator(title):
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)


def print_topic_list(topics, max_count=5):
    """打印话题列表"""
    for i, t in enumerate(topics[:max_count], 1):
        print(f"   {i}. [{t.source}] {t.title[:45]}...")


async def test_free_sources():
    """测试免费数据源"""
    print_separator("测试免费/开源源")
    
    sources = [
        ("DailyHot", DailyHotDataSource()),
        ("VVhan", VVhanDataSource()),
        ("WeiboFree", WeiboHotDataSource()),
        ("DouyinFree", DouyinHotDataSource()),
    ]
    
    results = {}
    
    for name, source in sources:
        available = source.is_available()
        print(f"\n{name}:")
        print(f"   可用性: {available}")
        
        if available:
            try:
                topics = await source.fetch(TEST_IP_PROFILE, 3)
                print(f"   获取数量: {len(topics)}")
                if topics:
                    print_topic_list(topics, 3)
                    results[name] = len(topics)
                else:
                    results[name] = 0
            except Exception as e:
                print(f"   ❌ 错误: {e}")
                results[name] = -1
        else:
            results[name] = -1
    
    return results


async def test_paid_sources():
    """测试付费数据源"""
    print_separator("测试付费数据源")
    
    sources = [
        ("顺为数据(ShunWei)", ShunWeiDataSource()),
        ("QQ来客源(QQLYKM)", QQLYKMDataSource()),
        ("今日热榜(TopHub)", TopHubDataSource()),
    ]
    
    results = {}
    
    for name, source in sources:
        available = source.is_available()
        print(f"\n{name}:")
        print(f"   可用性: {available}")
        
        if available:
            try:
                topics = await source.fetch(TEST_IP_PROFILE, 3)
                print(f"   获取数量: {len(topics)}")
                if topics:
                    print_topic_list(topics, 3)
                    results[name] = len(topics)
                else:
                    results[name] = 0
            except Exception as e:
                print(f"   ❌ 错误: {e}")
                results[name] = -1
        else:
            print(f"   ⚠️ 未配置API Key")
            results[name] = -1
    
    return results


async def test_platform_sources():
    """测试平台专属源"""
    print_separator("测试平台专属聚合源")
    
    sources = [
        ("小红书", XiaohongshuDataSource()),
        ("抖音", DouyinDataSource()),
        ("微博", WeiboDataSource()),
    ]
    
    results = {}
    
    for name, source in sources:
        available = source.is_available()
        print(f"\n{name}聚合源:")
        print(f"   可用性: {available}")
        
        try:
            topics = await source.fetch(TEST_IP_PROFILE, 5)
            print(f"   获取数量: {len(topics)}")
            if topics:
                print_topic_list(topics, 3)
                results[name] = len(topics)
            else:
                results[name] = 0
        except Exception as e:
            print(f"   ❌ 错误: {e}")
            results[name] = -1
    
    return results


async def test_manager_v2():
    """测试管理器V2"""
    print_separator("测试数据源管理器 V2")
    
    manager = get_datasource_manager_v2()
    
    # 1. 列出所有源
    print("\n1. 所有数据源:")
    sources = manager.list_sources()
    for s in sources:
        status = "✅" if s.get('health', {}).get('available') else "❌"
        print(f"   {status} {s['source_id']}: {s['name']} ({s['status']})")
    
    # 2. 可用源
    print("\n2. 可用数据源:")
    available = manager.list_available_sources()
    for s_id in available:
        print(f"   ✅ {s_id}")
    
    # 3. 测试不同策略
    print("\n3. 测试获取策略:")
    
    strategies = ["smart", "free_only", "platform"]
    
    for strategy in strategies:
        try:
            print(f"\n   策略 '{strategy}':")
            topics = await manager.fetch_with_strategy(TEST_IP_PROFILE, 6, strategy)
            print(f"      获取数量: {len(topics)}")
            if topics:
                # 统计来源
                sources_count = {}
                for t in topics:
                    src = t.source
                    sources_count[src] = sources_count.get(src, 0) + 1
                print(f"      来源分布: {sources_count}")
        except Exception as e:
            print(f"      ❌ 错误: {e}")
    
    # 4. 平台专属获取
    print("\n4. 平台专属获取:")
    for platform in ["xiaohongshu", "douyin", "weibo"]:
        try:
            topics = await manager.fetch_from_platform(platform, TEST_IP_PROFILE, 3)
            print(f"   {platform}: {len(topics)} 条")
        except Exception as e:
            print(f"   {platform}: ❌ {e}")
    
    return {"total_sources": len(sources), "available": len(available)}


async def print_config_guide():
    """打印配置指南"""
    print_separator("数据源配置指南")
    
    manager = get_datasource_manager_v2()
    guide = manager.get_data_source_guide()
    
    for category, sources in guide.items():
        print(f"\n{category}:")
        for source_id, info in sources.items():
            print(f"\n   {info['name']} ({source_id})")
            print(f"      描述: {info['description']}")
            print(f"      价格: {info['cost']}")
            print(f"      推荐: {info['priority']}")
            if info.get('url'):
                print(f"      链接: {info['url']}")
            if info.get('env_vars'):
                print(f"      环境变量: {', '.join(info['env_vars'])}")


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*80)
    print("  完整数据源测试套件")
    print("  " + str(datetime.now()))
    print("="*80)
    
    all_results = {}
    
    # 1. 测试免费源
    try:
        all_results["free"] = await test_free_sources()
    except Exception as e:
        print(f"免费源测试出错: {e}")
        all_results["free"] = {}
    
    # 2. 测试付费源
    try:
        all_results["paid"] = await test_paid_sources()
    except Exception as e:
        print(f"付费源测试出错: {e}")
        all_results["paid"] = {}
    
    # 3. 测试平台专属源
    try:
        all_results["platform"] = await test_platform_sources()
    except Exception as e:
        print(f"平台源测试出错: {e}")
        all_results["platform"] = {}
    
    # 4. 测试管理器
    try:
        all_results["manager"] = await test_manager_v2()
    except Exception as e:
        print(f"管理器测试出错: {e}")
        all_results["manager"] = {}
    
    # 5. 配置指南
    await print_config_guide()
    
    # 汇总
    print_separator("测试汇总")
    
    total_success = 0
    total_failed = 0
    
    for category, results in all_results.items():
        if isinstance(results, dict):
            for name, count in results.items():
                if isinstance(count, int):
                    if count > 0:
                        total_success += 1
                        status = f"✅ ({count}条)"
                    elif count == 0:
                        status = "⚠️ (无数据)"
                    else:
                        total_failed += 1
                        status = "❌ (失败)"
                    print(f"   {name}: {status}")
    
    print(f"\n总计: {total_success} 成功, {total_failed} 失败")
    
    if total_success > 0:
        print("\n✅ 至少有一个数据源可用，系统可正常工作")
    else:
        print("\n❌ 没有可用的数据源，请配置环境变量")
        print("\n推荐配置:")
        print("   1. 免费方案: DAILYHOT_API_URL=https://api-hot.imsyy.top")
        print("   2. 低成本方案: SHUNWEI_API_KEY=your_key (10元/月)")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
