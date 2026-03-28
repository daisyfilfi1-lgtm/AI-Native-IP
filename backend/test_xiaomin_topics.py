#!/usr/bin/env python3
"""
小敏操盘手测试脚本 - 验证推荐选题是否符合IP风格

测试目标：
1. 验证选题是否包含小敏IP核心关键词
2. 验证选题是否符合小敏IP的内容方向
3. 验证算法匹配逻辑是否正确
"""

import json
import requests
import sys
from datetime import datetime

# API配置
BASE_URL = "https://ai-native-ip-production.up.railway.app"
API_KEY = "test-key"  # 如果有API Key请替换

# 小敏IP核心标签（基于ip_config.json）
XIAOMIN_IP_PROFILE = {
    "ip_id": "xiaomin1",
    "name": "馒头女子",
    "nickname": "小敏",
    "expertise": "花样馒头制作/私域运营/短视频获客/团队培训",
    "content_direction": "花样馒头创业/女性独立/私域变现/短视频获客",
    "target_audience": "渴望经济独立、提升家庭地位的30-50岁宝妈及女性创业者",
    "market_demand": "低成本创业/女性副业/私房美食/健康早餐",
    "product_service": "花样馒头课程/私房创业班/四大场景模型/药食同源产品",
    "passion": "帮助女性创业/美食研发/个人成长",
}

# 白名单关键词（应该出现在选题中）
WHITELIST_KEYWORDS = [
    "创业", "翻身", "变现", "私域", "馒头", "花样馒头", 
    "女性", "宝妈", "副业", "低成本", "赚钱", "独立"
]

# 黑名单关键词（不应该出现在选题中）
BLACKLIST_KEYWORDS = [
    "医生", "医疗", "科普", "健康", "问诊", "医院", "药"
]

# 四大内容方向权重评估
CONTENT_DIRECTIONS = {
    "花样馒头创业": ["馒头", "花样馒头", "面食", "手艺", "制作"],
    "女性独立": ["女性", "宝妈", "独立", "经济独立", "家庭地位"],
    "私域变现": ["私域", "变现", "赚钱", "收入", "获客", "转化"],
    "低成本创业": ["低成本", "副业", "创业", "轻装上阵", "2000", "二手设备"]
}


def test_api_connection():
    """测试API连接"""
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=10)
        if resp.status_code == 200:
            print(f"✅ API连接正常: {resp.json()}")
            return True
        else:
            print(f"❌ API连接异常: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ API连接失败: {e}")
        return False


def fetch_recommended_topics(ip_id="xiaomin1", limit=12):
    """获取推荐选题"""
    headers = {"X-API-Key": API_KEY}
    params = {"ipId": ip_id, "limit": limit}
    
    try:
        resp = requests.get(
            f"{BASE_URL}/api/v1/creator/topics/recommended",
            headers=headers,
            params=params,
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json().get("topics", [])
        else:
            print(f"❌ 获取选题失败: {resp.status_code} - {resp.text}")
            return []
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return []


def analyze_topic_relevance(topic):
    """分析选题与IP的相关性"""
    title = topic.get("title", "")
    tags = topic.get("tags", [])
    reason = topic.get("reason", "")
    
    text = f"{title} {' '.join(tags)}".lower()
    
    # 1. 白名单匹配检查
    whitelist_matches = [kw for kw in WHITELIST_KEYWORDS if kw.lower() in text]
    
    # 2. 黑名单检查
    blacklist_matches = [kw for kw in BLACKLIST_KEYWORDS if kw.lower() in text]
    
    # 3. 内容方向匹配分析
    direction_scores = {}
    for direction, keywords in CONTENT_DIRECTIONS.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        direction_scores[direction] = score
    
    # 4. 判断匹配方式
    if "热点迁移" in reason:
        match_method = "IP角度改写"
    elif "四维重排" in reason:
        match_method = "关键词/语义匹配"
    elif "快照兜底" in reason:
        match_method = "内置快照"
    elif "算法兜底" in reason:
        match_method = "IP算法生成"
    else:
        match_method = "未知"
    
    return {
        "whitelist_matches": whitelist_matches,
        "blacklist_matches": blacklist_matches,
        "direction_scores": direction_scores,
        "match_method": match_method,
        "has_whitelist": len(whitelist_matches) > 0,
        "has_blacklist": len(blacklist_matches) > 0,
    }


def evaluate_topics(topics):
    """评估选题列表"""
    print(f"\n{'='*80}")
    print(f"📊 小敏IP推荐选题评估报告")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    if not topics:
        print("❌ 未获取到任何选题")
        return
    
    print(f"📋 共获取 {len(topics)} 个选题\n")
    
    # 统计变量
    stats = {
        "total": len(topics),
        "has_whitelist": 0,
        "has_blacklist": 0,
        "by_method": {},
        "by_direction": {k: 0 for k in CONTENT_DIRECTIONS.keys()},
        "direction_scores": {k: [] for k in CONTENT_DIRECTIONS.keys()},
    }
    
    for i, topic in enumerate(topics, 1):
        print(f"\n{'─'*80}")
        print(f"【选题 {i}】评分: {topic.get('score', 0)}")
        print(f"{'─'*80}")
        print(f"📌 标题: {topic.get('title', '')}")
        print(f"🏷️  标签: {', '.join(topic.get('tags', []))}")
        print(f"💡 原因: {topic.get('reason', '')}")
        
        analysis = analyze_topic_relevance(topic)
        
        # 白名单匹配
        if analysis["has_whitelist"]:
            print(f"✅ 白名单匹配: {', '.join(analysis['whitelist_matches'])}")
            stats["has_whitelist"] += 1
        else:
            print(f"⚠️  未命中白名单关键词")
        
        # 黑名单检查
        if analysis["has_blacklist"]:
            print(f"❌ 黑名单命中: {', '.join(analysis['blacklist_matches'])}")
            stats["has_blacklist"] += 1
        
        # 匹配方式
        method = analysis["match_method"]
        print(f"🔍 匹配方式: {method}")
        stats["by_method"][method] = stats["by_method"].get(method, 0) + 1
        
        # 内容方向评分
        print(f"📈 内容方向匹配:")
        for direction, score in analysis["direction_scores"].items():
            bar = "█" * score + "░" * (5 - score)
            print(f"   {direction:12s} [{bar}] {score}")
            if score > 0:
                stats["by_direction"][direction] += 1
            stats["direction_scores"][direction].append(score)
    
    # 汇总报告
    print(f"\n{'='*80}")
    print(f"📊 汇总统计")
    print(f"{'='*80}\n")
    
    print(f"✅ 命中白名单: {stats['has_whitelist']}/{stats['total']} ({stats['has_whitelist']/stats['total']*100:.1f}%)")
    print(f"❌ 命中黑名单: {stats['has_blacklist']}/{stats['total']}")
    
    print(f"\n🔍 匹配方式分布:")
    for method, count in stats["by_method"].items():
        pct = count / stats["total"] * 100
        print(f"   {method}: {count} ({pct:.1f}%)")
    
    print(f"\n📈 内容方向覆盖:")
    for direction, count in stats["by_direction"].items():
        pct = count / stats["total"] * 100
        avg_score = sum(stats["direction_scores"][direction]) / stats["total"]
        print(f"   {direction}: {count}/{stats['total']} ({pct:.1f}%) 平均匹配度: {avg_score:.2f}")
    
    # 综合评估
    print(f"\n{'='*80}")
    print(f"🎯 综合评估")
    print(f"{'='*80}\n")
    
    # 评估标准
    if stats["has_whitelist"] >= stats["total"] * 0.5:
        whitelist_grade = "✅ 优秀"
    elif stats["has_whitelist"] >= stats["total"] * 0.3:
        whitelist_grade = "⚠️  一般"
    else:
        whitelist_grade = "❌ 较差"
    
    best_direction = max(stats["by_direction"].items(), key=lambda x: x[1])
    if best_direction[1] >= stats["total"] * 0.5:
        direction_grade = f"✅ 优秀（主要覆盖：{best_direction[0]}）"
    elif best_direction[1] >= stats["total"] * 0.3:
        direction_grade = f"⚠️  一般（主要覆盖：{best_direction[0]}）"
    else:
        direction_grade = "❌ 较差（内容方向分散）"
    
    print(f"关键词匹配度: {whitelist_grade}")
    print(f"内容方向集中度: {direction_grade}")
    
    if stats["has_blacklist"] > 0:
        print(f"⚠️  警告: 有 {stats['has_blacklist']} 个选题命中黑名单，建议人工审核")
    
    # 建议
    print(f"\n💡 优化建议:")
    if stats["has_whitelist"] < stats["total"] * 0.5:
        print(f"   1. 增加更多与小敏IP相关的白名单关键词")
        print(f"   2. 优化语义匹配算法，提高关键词匹配率")
    if best_direction[1] < stats["total"] * 0.4:
        print(f"   3. 选题内容方向分散，建议聚焦核心方向（花样馒头创业、女性独立）")
    if "IP角度改写" in stats["by_method"] and stats["by_method"]["IP角度改写"] > stats["total"] * 0.5:
        print(f"   4. 过多选题使用'IP角度改写'，建议优化白名单以直接匹配更多热点")
    
    print(f"\n{'='*80}\n")


def main():
    """主函数"""
    print("🚀 启动小敏IP推荐选题测试...")
    
    # 测试API连接
    if not test_api_connection():
        print("\n⚠️  尝试使用本地数据测试...")
        # 使用本地保存的creator_topics.json
        try:
            with open("creator_topics.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                topics = data.get("topics", [])
                evaluate_topics(topics)
        except FileNotFoundError:
            print("❌ 本地数据文件不存在")
        return
    
    # 获取推荐选题
    print("\n📡 正在获取推荐选题...")
    topics = fetch_recommended_topics(ip_id="xiaomin1", limit=12)
    
    # 评估选题
    evaluate_topics(topics)
    
    # 保存结果
    output_file = f"xiaomin_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"topics": topics}, f, ensure_ascii=False, indent=2)
    print(f"💾 结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
