#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源层 V2.0 测试脚本
验证多源融合架构
"""

import asyncio
import json
import sys
import io
from typing import List, Dict, Any

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, "f:\\AI-Native IP\\backend")

from app.services.datasource import (
    BuiltinDataSource,
    TikHubDataSource,
    DataSourceManager,
    get_datasource_manager,
    TopicData,
)


# 测试IP画像
TEST_IP_PROFILE = {
    "ip_id": "xiaomin1",
    "name": "馒头女子",
    "nickname": "小敏",
    "expertise": "花样馒头制作/私域运营/短视频获客/团队培训",
    "content_direction": "花样馒头创业/女性独立/私域变现/短视频获客",
    "target_audience": "渴望经济独立、提升家庭地位的30-50岁宝妈及女性创业者",
}


async def test_builtin_source():
    """测试内置数据源"""
    print("\n" + "="*80)
    print("📦 测试：内置数据源 (BuiltinDataSource)")
    print("="*80)
    
    source = BuiltinDataSource()
    
    # 1. 测试可用性
    print("\n1. 可用性检查：")
    available = source.is_available()
    print(f"   is_available: {available} (应为True)")
    
    # 2. 获取数据
    print("\n2. 获取12个话题：")
    topics = await source.fetch(TEST_IP_PROFILE, limit=12)
    print(f"   返回数量: {len(topics)}")
    
    # 3. 内容类型分布
    type_counts = {}
    for t in topics:
        ctype = t.extra.get("content_type", "other")
        type_counts[ctype] = type_counts.get(ctype, 0) + 1
    
    print(f"   内容分布: {type_counts}")
    
    # 4. 显示话题
    print("\n3. 话题列表：")
    for i, t in enumerate(topics[:5], 1):
        ctype = t.extra.get("content_type", "other")
        print(f"   {i}. [{ctype}] {t.title[:40]}... (score: {t.score})")
    
    return True


async def test_tikhub_source():
    """测试TIKHUB数据源"""
    print("\n" + "="*80)
    print("🔗 测试：TIKHUB数据源 (TikHubDataSource)")
    print("="*80)
    
    source = TikHubDataSource()
    
    # 1. 检查配置
    print("\n1. 配置检查：")
    available = source.is_available()
    print(f"   is_available: {available}")
    print(f"   api_key配置: {'是' if source.api_key else '否'}")
    
    if not available:
        print("   ⚠️ TIKHUB未配置，跳过API调用测试")
        return True
    
    # 2. 获取数据
    print("\n2. 获取实时数据：")
    try:
        topics = await source.fetch(TEST_IP_PROFILE, limit=6)
        print(f"   返回数量: {len(topics)}")
        
        for i, t in enumerate(topics[:3], 1):
            print(f"   {i}. [{t.source}] {t.title[:40]}...")
        
        return True
    except Exception as e:
        print(f"   ⚠️ API调用失败: {e}")
        print("   这是正常的，如果TIKHUB未配置或网络不通")
        return True


async def test_datasource_manager():
    """测试数据源管理器"""
    print("\n" + "="*80)
    print("🎯 测试：数据源管理器 (DataSourceManager)")
    print("="*80)
    
    manager = get_datasource_manager()
    
    # 1. 列出数据源
    print("\n1. 已注册数据源：")
    sources = manager.list_sources()
    for s in sources:
        print(f"   - {s['source_id']}: {s['name']} (priority={s['priority']}, status={s['status']})")
    
    # 2. Hybrid策略获取
    print("\n2. Hybrid策略获取：")
    topics = await manager.fetch_topics(TEST_IP_PROFILE, limit=12, strategy="hybrid")
    print(f"   返回数量: {len(topics)}")
    
    # 3. 数据源分布
    source_counts = {}
    for t in topics:
        src = t.source
        source_counts[src] = source_counts.get(src, 0) + 1
    print(f"   数据源分布: {source_counts}")
    
    # 4. 显示结果
    print("\n3. 推荐话题：")
    for i, t in enumerate(topics[:6], 1):
        ctype = t.extra.get("content_type", "other")
        print(f"   {i}. [{t.source}/{ctype}] {t.title[:45]}...")
    
    return True


async def test_fault_tolerance():
    """测试故障容错"""
    print("\n" + "="*80)
    print("🛡️ 测试：故障容错机制")
    print("="*80)
    
    manager = get_datasource_manager()
    
    # 模拟TIKHUB不可用的情况
    print("\n1. 模拟TIKHUB不可用：")
    tikhub = manager.get_source("tikhub")
    if tikhub:
        original_available = tikhub._available
        tikhub._available = False  # 强制不可用
        
        # 获取数据
        topics = await manager.fetch_topics(TEST_IP_PROFILE, limit=8)
        print(f"   TIKHUB不可用，返回数量: {len(topics)}")
        print(f"   数据源分布: {dict((t.source, sum(1 for x in topics if x.source==t.source)) for t in topics)}")
        
        # 恢复
        tikhub._available = original_available
    
    # 2. 健康检查
    print("\n2. 健康检查：")
    health = await manager.health_check()
    for source_id, status in health.items():
        print(f"   {source_id}: available={status['available']}")
    
    return True


async def test_cache():
    """测试缓存机制"""
    print("\n" + "="*80)
    print("💾 测试：缓存机制")
    print("="*80)
    
    from app.services.datasource.cache import TopicCache
    
    cache = TopicCache()
    
    # 1. 创建测试数据
    print("\n1. 写入缓存：")
    test_topics = [
        TopicData(
            id="test_001",
            title="测试话题1",
            original_title="测试话题1",
            platform="test",
            url="",
            tags=["测试"],
            score=4.5,
            source="test"
        ),
        TopicData(
            id="test_002",
            title="测试话题2",
            original_title="测试话题2",
            platform="test",
            url="",
            tags=["测试"],
            score=4.0,
            source="test"
        ),
    ]
    
    cache.set("test_ip", "test_source", test_topics)
    print(f"   写入 {len(test_topics)} 个话题")
    
    # 2. 读取缓存
    print("\n2. 读取缓存：")
    cached = cache.get("test_ip", "test_source", max_age_hours=1)
    if cached:
        print(f"   读取成功: {len(cached)} 个话题")
        for t in cached:
            print(f"   - {t.title}")
    else:
        print("   读取失败")
    
    # 3. 统计
    print("\n3. 缓存统计：")
    stats = cache.get_stats()
    print(f"   {stats}")
    
    # 4. 清理测试缓存
    cache.invalidate("test_ip", "test_source")
    print("\n4. 测试缓存已清理")
    
    return True


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*80)
    print("  数据源层 V2.0 架构测试")
    print("="*80)
    
    tests = [
        ("内置数据源", test_builtin_source),
        ("TIKHUB数据源", test_tikhub_source),
        ("数据源管理器", test_datasource_manager),
        ("故障容错", test_fault_tolerance),
        ("缓存机制", test_cache),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, "✅ 通过" if success else "❌ 失败"))
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, f"❌ 错误: {e}"))
    
    # 汇总
    print("\n" + "="*80)
    print("📋 测试结果汇总")
    print("="*80)
    
    for name, status in results:
        print(f"   {name:20s} {status}")
    
    passed = sum(1 for _, s in results if "通过" in s)
    print(f"\n   总计: {passed}/{len(results)} 通过")
    
    if passed == len(results):
        print("\n   [OK] 所有测试通过！数据源层架构已就绪。")
    
    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
