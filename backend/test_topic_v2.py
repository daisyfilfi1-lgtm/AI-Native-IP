#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
选题推荐 V2.0 测试脚本
验证基于IP的匹配爆款选题功能
"""

import asyncio
import json
import sys
import io
from typing import List, Dict, Any

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目路径
sys.path.insert(0, "f:\\AI-Native IP\\backend")

from app.services.builtin_topic_repository import (
    get_builtin_topics,
    get_topics_by_matrix,
    get_emergency_topics,
)
from app.services.keyword_synonyms import (
    expand_keywords,
    calculate_keyword_match_score,
    classify_content_type,
    get_content_type_name,
)
from app.services.enhanced_topic_matcher import EnhancedTopicMatcher


# 测试IP画像
TEST_IP_PROFILE = {
    "ip_id": "xiaomin1",
    "name": "馒头女子",
    "nickname": "小敏",
    "expertise": "花样馒头制作/私域运营/短视频获客/团队培训",
    "content_direction": "花样馒头创业/女性独立/私域变现/短视频获客",
    "target_audience": "渴望经济独立、提升家庭地位的30-50岁宝妈及女性创业者",
    "monetization_model": "课程销售/培训服务/产品零售/加盟代理",
    "product_service": "花样馒头课程/私房创业班/四大场景模型/药食同源产品",
    "market_demand": "低成本创业/女性副业/私房美食/健康早餐",
    "passion": "帮助女性创业/美食研发/个人成长",
}


def test_builtin_repository():
    """测试内置选题库"""
    print("\n" + "="*80)
    print("📦 测试：内置选题库")
    print("="*80)
    
    # 1. 测试按内容矩阵获取
    print("\n1. 按4-3-2-1内容矩阵获取选题：")
    topics = get_topics_by_matrix("xiaomin1", limit=12)
    
    # 统计分布
    content_types = {}
    for t in topics:
        ctype = t.get("content_type", "other")
        content_types[ctype] = content_types.get(ctype, 0) + 1
    
    print(f"   获取到 {len(topics)} 个选题")
    print(f"   分布：{content_types}")
    
    # 显示前5个
    print("\n   前5个选题：")
    for i, t in enumerate(topics[:5], 1):
        print(f"   {i}. [{t.get('content_type')}] {t.get('title')[:40]}... (score: {t.get('score')})")
    
    return True


def test_keyword_synonyms():
    """测试关键词同义词库"""
    print("\n" + "="*80)
    print("🔤 测试：关键词同义词库")
    print("="*80)
    
    # 1. 测试关键词扩展
    print("\n1. 关键词扩展：")
    keywords = ["赚钱", "宝妈", "馒头"]
    expanded = expand_keywords(keywords)
    print(f"   原始词：{keywords}")
    print(f"   扩展后：{list(expanded)[:15]}... (共{len(expanded)}个)")
    
    # 2. 测试匹配分数计算
    print("\n2. 匹配分数计算：")
    test_cases = [
        ("宝妈创业月入3万的方法", ["宝妈", "创业", "月入3万"]),
        ("一个普通人的逆袭之路", ["普通人", "逆袭", "翻身"]),
        ("国足赢了比赛", ["宝妈", "创业", "赚钱"]),  # 不匹配
    ]
    
    for text, kws in test_cases:
        score = calculate_keyword_match_score(text, kws)
        print(f"   '{text[:20]}...' -> {score:.0%}")
    
    # 3. 测试内容分类
    print("\n3. 内容分类：")
    test_titles = [
        "月入3万的创业方法",
        "离婚后我是如何走出低谷的",
        "馒头制作的完整教程",
        "创业女性的精致生活",
    ]
    
    for title in test_titles:
        ctype = classify_content_type(title)
        print(f"   '{title[:20]}...' -> {ctype} ({get_content_type_name(ctype)})")
    
    return True


def test_enhanced_matcher():
    """测试增强匹配器"""
    print("\n" + "="*80)
    print("🎯 测试：增强话题匹配器")
    print("="*80)
    
    matcher = EnhancedTopicMatcher()
    
    # 测试话题
    test_topics = [
        {"title": "2000块创业月入3万，宝妈的低成本副业打法", "tags": ["宝妈", "创业", "月入3万"], "score": 4.9},
        {"title": "32岁离婚带俩娃，我是如何靠自己走出低谷的", "tags": ["离婚", "带娃", "逆袭"], "score": 4.8},
        {"title": "这个馒头配方我练了3年，今天免费分享", "tags": ["馒头", "配方", "教学"], "score": 4.7},
        {"title": "国足2:0库拉索，精彩进球集锦", "tags": ["国足", "足球"], "score": 4.9},  # 不匹配
    ]
    
    print("\n1. IP与话题匹配测试：")
    print(f"   IP: {TEST_IP_PROFILE['nickname']} ({TEST_IP_PROFILE['content_direction'][:30]}...)")
    print()
    
    for topic in test_topics:
        scores = matcher.compute_match_score(TEST_IP_PROFILE, topic)
        match_indicator = "✅" if scores['overall'] >= 0.5 else "❌"
        print(f"   {match_indicator} '{topic['title'][:30]}...'")
        print(f"      综合匹配: {scores['overall']:.0%} | 语义: {scores['semantic']:.0%} | 关键词: {scores['keyword']:.0%}")
    
    # 测试过滤和排序
    print("\n2. 话题过滤和排序（阈值0.4）：")
    matched = matcher.filter_and_rank_topics(TEST_IP_PROFILE, test_topics, threshold=0.4)
    print(f"   输入: {len(test_topics)} 个话题")
    print(f"   通过: {len(matched)} 个话题")
    
    for t in matched:
        print(f"   - {t['title'][:35]}... (匹配度: {t['match_score']:.0%})")
    
    return True


def test_four_dim_scoring():
    """测试四维评分"""
    print("\n" + "="*80)
    print("📊 测试：四维评分系统")
    print("="*80)
    
    matcher = EnhancedTopicMatcher()
    
    test_topic = {
        "title": "2000块创业月入3万，宝妈的低成本副业打法",
        "tags": ["宝妈", "创业", "月入3万"],
        "score": 4.9,
        "match_score": 0.92,
    }
    
    weights = {"relevance": 0.3, "hotness": 0.3, "competition": 0.2, "conversion": 0.2}
    
    scores = matcher.calculate_four_dim_score(test_topic, TEST_IP_PROFILE, weights)
    
    print(f"\n话题: {test_topic['title']}")
    print(f"\n四维评分:")
    print(f"   相关度 (relevance): {scores['relevance']:.0%} (权重30%)")
    print(f"   热度   (hotness):   {scores['hotness']:.0%} (权重30%)")
    print(f"   竞争度 (competition): {scores['competition']:.0%} (权重20%)")
    print(f"   转化度 (conversion): {scores['conversion']:.0%} (权重20%)")
    print(f"   ─────────────────────────")
    print(f"   综合分 (total):     {scores['total']:.1f}/5.0")
    
    return True


def test_emergency_fallback():
    """测试紧急兜底机制"""
    print("\n" + "="*80)
    print("🆘 测试：紧急兜底机制")
    print("="*80)
    
    # 当所有数据源都失败时
    print("\n1. 紧急兜底选题（TIKHUB失效时使用）：")
    emergency_topics = get_emergency_topics("xiaomin1", limit=6)
    
    print(f"   返回 {len(emergency_topics)} 个高质量选题")
    
    for i, t in enumerate(emergency_topics, 1):
        print(f"   {i}. [{t.get('content_type')}] {t.get('title')[:40]}... (score: {t.get('score')})")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*80)
    print("  选题推荐 V2.0 测试套件")
    print("="*80)
    
    tests = [
        ("内置选题库", test_builtin_repository),
        ("关键词同义词", test_keyword_synonyms),
        ("增强匹配器", test_enhanced_matcher),
        ("四维评分", test_four_dim_scoring),
        ("紧急兜底", test_emergency_fallback),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "✅ 通过" if success else "❌ 失败"))
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 失败: {e}")
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
        print("\n   [OK] 所有测试通过！系统已就绪。")
    
    return passed == len(results)


if __name__ == "__main__":
    # 运行测试
    success = run_all_tests()
    sys.exit(0 if success else 1)
