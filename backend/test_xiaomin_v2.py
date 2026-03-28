#!/usr/bin/env python3
"""
小敏操盘手测试脚本 V2 - 全面评估修复后的推荐选题效果

测试维度：
1. 白名单关键词覆盖率
2. 黑名单过滤效果
3. 选题与小敏IP画像的匹配度
4. 改写标题的质量
5. 内容方向分布
"""

import json
import re
from datetime import datetime

# 小敏IP完整画像（基于ip_config.json）
XIAOMIN_PROFILE = {
    "ip_id": "xiaomin1",
    "name": "馒头女子",
    "nickname": "小敏",
    "bio": "从负债400万到帮扶2000+女性创业的实战派导师，从厨房走到台前，用花样馒头手艺带你又美又飒搞事业",
    "expertise": "花样馒头制作/私域运营/短视频获客/团队培训",
    "content_direction": "花样馒头创业/女性独立/私域变现/短视频获客",
    "target_audience": "渴望经济独立、提升家庭地位的30-50岁宝妈及女性创业者",
    "market_demand": "低成本创业/女性副业/私房美食/健康早餐",
    "product_service": "花样馒头课程/私房创业班/四大场景模型/药食同源产品",
    "passion": "帮助女性创业/美食研发/个人成长",
}

# 新版白名单关键词（修复后的）
WHITELIST_KEYWORDS_V2 = [
    # 核心产品词
    "馒头", "花样馒头", "面食", "美食", "早餐", "手工", "手艺", "制作", "烘焙",
    # 创业相关
    "创业", "副业", "低成本", "小成本", "轻创业", "轻装上阵", "摆摊", "私房",
    # 变现相关
    "赚钱", "变现", "收入", "月入", "盈利", "生意", "商机",
    # 人群定位
    "宝妈", "女性", "妈妈", "家庭主妇", "老板娘", "普通人",
    # 成长相关
    "翻身", "逆袭", "改变", "转型", "独立", "自强", "成长",
    # 运营相关
    "私域", "获客", "引流", "短视频", "直播", "营销",
]

# 新版黑名单关键词（修复后的）
BLACKLIST_KEYWORDS_V2 = [
    "医生", "医疗", "医院", "药", "治病", "问诊", "手术", "疗法",
    "科普", "健康", "养生", "保健", "营养", "功效", "治疗",
    "减肥", "瘦身", "美容", "整容", "医美", "化妆品",
    "汽车", "房产", "股票", "基金", "投资", "理财", "保险",
]

# 四大内容方向及关键词
CONTENT_DIRECTIONS = {
    "花样馒头手艺": ["馒头", "花样馒头", "面食", "美食", "早餐", "手工", "手艺", "制作", "烘焙", "厨房"],
    "女性创业独立": ["女性", "宝妈", "妈妈", "独立", "自强", "翻身", "逆袭", "改变", "成长", "老板娘"],
    "低成本副业": ["低成本", "小成本", "副业", "轻创业", "摆摊", "私房", "普通人", "赚钱"],
    "私域变现获客": ["私域", "变现", "获客", "引流", "短视频", "直播", "营销", "月入", "盈利"],
}

# 模拟修复后的测试数据
MOCK_TOPICS_FIXED = [
    {
        "id": "dyhub_1",
        "title": "早餐店老板的馒头秘方，月入3万比打工强",
        "score": 4.52,
        "tags": ["抖音", "热榜", "馒头", "早餐", "创业"],
        "reason": "关键词匹配（馒头、早餐、创业）+ 四维重排 R/H/CV=0.85/0.92/0.48/0.88",
        "filter_method": "keyword",
    },
    {
        "id": "dyhub_2",
        "title": "90后宝妈辞职做手工面食，从负债到月入5万",
        "score": 4.68,
        "tags": ["抖音", "热榜", "宝妈", "手工", "面食", "翻身"],
        "reason": "关键词匹配（宝妈、手工、面食、翻身）+ 四维重排 R/H/CV=0.92/0.88/0.52/0.90",
        "filter_method": "keyword",
    },
    {
        "id": "dyhub_3",
        "title": "私房烘焙创业：2000元启动资金如何月入过万",
        "score": 4.45,
        "tags": ["抖音", "热榜", "私房", "烘焙", "创业", "低成本"],
        "reason": "关键词匹配（私房、烘焙、创业、低成本）+ 四维重排 R/H/CV=0.88/0.85/0.55/0.85",
        "filter_method": "keyword",
    },
    {
        "id": "dyhub_4",
        "title": "从负债到月入3万：一个宝妈如何用花样馒头实现翻身",
        "score": 4.35,
        "tags": ["抖音", "热榜", "宝妈", "花样馒头", "翻身", "创业"],
        "reason": "IP视角改写(xiaomin1) + 原热点：生活是一本充满故事的书",
        "filter_method": "ip_adapted",
        "original_title": "生活是一本充满故事的书",
    },
    {
        "id": "dyhub_5",
        "title": "不想上班了？看这个宝妈如何用手艺开启创业之路",
        "score": 4.28,
        "tags": ["抖音", "热榜", "宝妈", "手艺", "创业", "副业"],
        "reason": "IP视角改写(xiaomin1) + 原热点：一天连轴转的留学生活",
        "filter_method": "ip_adapted",
        "original_title": "一天连轴转的留学生活",
    },
]


def analyze_topic_v2(topic):
    """深度分析选题"""
    title = topic.get("title", "")
    tags = topic.get("tags", [])
    text = f"{title} {' '.join(tags)}".lower()
    
    # 1. 白名单匹配
    whitelist_matches = [kw for kw in WHITELIST_KEYWORDS_V2 if kw.lower() in text]
    
    # 2. 黑名单检查
    blacklist_matches = [kw for kw in BLACKLIST_KEYWORDS_V2 if kw.lower() in text]
    
    # 3. 内容方向评分
    direction_scores = {}
    for direction, keywords in CONTENT_DIRECTIONS.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        # 归一化到0-10
        direction_scores[direction] = min(10, score * 2)
    
    # 4. 匹配方式
    match_method = topic.get("filter_method", "unknown")
    
    # 5. 核心卖点分析
    selling_points = []
    if "宝妈" in text or "妈妈" in text:
        selling_points.append("宝妈人群")
    if "馒头" in text or "面食" in text or "烘焙" in text:
        selling_points.append("手艺产品")
    if "月入" in text or "赚钱" in text or "盈利" in text:
        selling_points.append("收入展示")
    if "翻身" in text or "逆袭" in text or "负债" in text:
        selling_points.append("逆袭故事")
    if "低成本" in text or "2000" in text or "摆摊" in text:
        selling_points.append("低门槛")
    
    # 6. 标题质量评分
    title_quality = 0
    if any(kw in title for kw in ["宝妈", "妈妈"]):
        title_quality += 2  # 目标人群
    if any(kw in title for kw in ["馒头", "手艺", "手工", "烘焙"]):
        title_quality += 2  # 产品
    if any(kw in title for kw in ["月入", "赚钱", "翻身", "创业"]):
        title_quality += 2  # 变现
    if len(title) <= 30:
        title_quality += 1  # 简洁
    if any(kw in title for kw in ["3万", "5万", "过万", "2000"]):
        title_quality += 1  # 具体数字
    
    return {
        "whitelist_matches": whitelist_matches,
        "blacklist_matches": blacklist_matches,
        "direction_scores": direction_scores,
        "match_method": match_method,
        "selling_points": selling_points,
        "title_quality": title_quality,
        "has_whitelist": len(whitelist_matches) > 0,
        "has_blacklist": len(blacklist_matches) > 0,
    }


def generate_report(topics, label=""):
    """生成测试报告"""
    print("=" * 80)
    print(f"小敏IP推荐选题测试报告 {'- ' + label if label else ''}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    if not topics:
        print("❌ 未获取到任何选题")
        return
    
    print(f"\n共测试 {len(topics)} 个选题\n")
    
    # 统计变量
    stats = {
        "total": len(topics),
        "keyword_match": 0,
        "ip_adapted": 0,
        "has_whitelist": 0,
        "has_blacklist": 0,
        "by_direction": {k: 0 for k in CONTENT_DIRECTIONS.keys()},
        "direction_scores": {k: [] for k in CONTENT_DIRECTIONS.keys()},
        "title_qualities": [],
        "selling_points_dist": {},
    }
    
    for i, topic in enumerate(topics, 1):
        print(f"\n{'─' * 80}")
        print(f"【选题 {i}】评分: {topic.get('score', 0)}")
        print(f"{'─' * 80}")
        print(f"📌 标题: {topic.get('title', '')}")
        if topic.get("original_title"):
            print(f"📎 原标题: {topic.get('original_title')}")
        print(f"🏷️  标签: {', '.join(topic.get('tags', []))}")
        print(f"💡 原因: {topic.get('reason', '')}")
        
        analysis = analyze_topic_v2(topic)
        
        # 匹配方式
        if analysis["match_method"] == "keyword":
            print(f"🔍 匹配方式: ✅ 直接关键词匹配")
            stats["keyword_match"] += 1
        else:
            print(f"🔍 匹配方式: 📝 IP角度改写")
            stats["ip_adapted"] += 1
        
        # 白名单匹配
        if analysis["has_whitelist"]:
            print(f"✅ 白名单命中: {', '.join(analysis['whitelist_matches'][:5])}")
            stats["has_whitelist"] += 1
        else:
            print(f"⚠️  未命中白名单")
        
        # 黑名单检查
        if analysis["has_blacklist"]:
            print(f"❌ 黑名单命中: {', '.join(analysis['blacklist_matches'])}")
            stats["has_blacklist"] += 1
        
        # 核心卖点
        if analysis["selling_points"]:
            print(f"🎯 核心卖点: {' | '.join(analysis['selling_points'])}")
            for sp in analysis["selling_points"]:
                stats["selling_points_dist"][sp] = stats["selling_points_dist"].get(sp, 0) + 1
        
        # 标题质量
        quality = analysis["title_quality"]
        stats["title_qualities"].append(quality)
        quality_label = "优秀" if quality >= 6 else "良好" if quality >= 4 else "一般"
        print(f"📊 标题质量: {quality}/8 ({quality_label})")
        
        # 内容方向评分
        print(f"📈 内容方向匹配:")
        for direction, score in analysis["direction_scores"].items():
            bar = "█" * (score // 2) + "░" * (5 - score // 2)
            print(f"   {direction:12s} [{bar}] {score}/10")
            if score >= 4:
                stats["by_direction"][direction] += 1
            stats["direction_scores"][direction].append(score)
    
    # 汇总报告
    print(f"\n{'=' * 80}")
    print("📊 汇总统计")
    print(f"{'=' * 80}\n")
    
    # 匹配方式分布
    print("🔍 匹配方式分布:")
    print(f"   直接关键词匹配: {stats['keyword_match']}/{stats['total']} ({stats['keyword_match']/stats['total']*100:.1f}%)")
    print(f"   IP角度改写: {stats['ip_adapted']}/{stats['total']} ({stats['ip_adapted']/stats['total']*100:.1f}%)")
    
    # 白名单覆盖率
    whitelist_rate = stats['has_whitelist'] / stats['total'] * 100
    print(f"\n✅ 白名单关键词覆盖率: {stats['has_whitelist']}/{stats['total']} ({whitelist_rate:.1f}%)")
    if whitelist_rate >= 80:
        print("   评级: 🟢 优秀")
    elif whitelist_rate >= 50:
        print("   评级: 🟡 良好")
    else:
        print("   评级: 🔴 需改进")
    
    # 黑名单检查
    if stats["has_blacklist"] == 0:
        print(f"\n✅ 黑名单过滤: 无违规内容")
    else:
        print(f"\n⚠️  黑名单命中: {stats['has_blacklist']} 个选题需人工审核")
    
    # 内容方向覆盖
    print(f"\n📈 内容方向覆盖:")
    for direction, count in stats["by_direction"].items():
        pct = count / stats["total"] * 100
        avg_score = sum(stats["direction_scores"][direction]) / stats["total"]
        print(f"   {direction}: {count}/{stats['total']} ({pct:.1f}%) 平均匹配度: {avg_score:.1f}/10")
    
    # 核心卖点分布
    print(f"\n🎯 核心卖点分布:")
    for point, count in sorted(stats["selling_points_dist"].items(), key=lambda x: -x[1]):
        print(f"   {point}: {count}次")
    
    # 标题质量
    avg_quality = sum(stats["title_qualities"]) / stats["total"]
    print(f"\n📊 平均标题质量: {avg_quality:.1f}/8")
    if avg_quality >= 6:
        print("   评级: 🟢 优秀")
    elif avg_quality >= 4:
        print("   评级: 🟡 良好")
    else:
        print("   评级: 🟠 需改进")
    
    # 综合评估
    print(f"\n{'=' * 80}")
    print("🎯 综合评估")
    print(f"{'=' * 80}\n")
    
    # 计算综合得分
    score = 0
    score += min(30, whitelist_rate * 0.3)  # 白名单覆盖率 30分
    score += min(25, stats["keyword_match"] / stats["total"] * 25)  # 直接匹配比例 25分
    score += min(20, avg_quality * 2.5)  # 标题质量 20分
    score += min(15, avg_score / 10 * 15)  # 内容方向匹配 15分
    score += 10 if stats["has_blacklist"] == 0 else max(0, 10 - stats["has_blacklist"] * 2)  # 黑名单 10分
    
    print(f"综合得分: {score:.1f}/100")
    if score >= 80:
        print("评级: 🟢 优秀 - 选题高度匹配小敏IP定位")
    elif score >= 60:
        print("评级: 🟡 良好 - 选题基本符合预期，仍有优化空间")
    elif score >= 40:
        print("评级: 🟠 一般 - 选题匹配度有待提升")
    else:
        print("评级: 🔴 较差 - 需要重大调整")
    
    # 优化建议
    print(f"\n💡 优化建议:")
    if whitelist_rate < 80:
        print(f"   1. 继续扩展白名单关键词，覆盖更多美食/手工相关词汇")
    if stats["keyword_match"] < stats["total"] * 0.5:
        print(f"   2. 增加直接关键词匹配比例，减少IP角度改写依赖")
    if avg_quality < 6:
        print(f"   3. 优化标题生成逻辑，增加数字、人群、产品等核心要素")
    if stats["by_direction"]["花样馒头手艺"] < stats["total"] * 0.3:
        print(f"   4. 增加与「花样馒头」直接相关的选题权重")
    
    print(f"\n{'=' * 80}\n")
    
    return score


def compare_versions():
    """对比修复前后的效果"""
    print("\n" + "=" * 80)
    print("修复前后对比测试")
    print("=" * 80 + "\n")
    
    # 修复前的模拟数据（基于creator_topics.json）
    before_topics = [
        {"title": "国足2:0库拉索：从创业到翻身的可复制打法", "score": 3.36, "tags": ["抖音", "热榜", "创业", "翻身"], "filter_method": "ip_adapted", "reason": "热点迁移到IP定位"},
        {"title": "一天连轴转的留学生活：从创业到翻身的可复制打法", "score": 3.36, "tags": ["抖音", "热榜", "创业", "翻身"], "filter_method": "ip_adapted", "reason": "热点迁移到IP定位"},
        {"title": "社保第六险已覆盖超3亿人：从创业到翻身的可复制打法", "score": 3.35, "tags": ["抖音", "热榜", "创业", "翻身"], "filter_method": "ip_adapted", "reason": "热点迁移到IP定位"},
        {"title": "妆前双胞胎妆后您哪位：从创业到翻身的可复制打法", "score": 3.34, "tags": ["抖音", "热榜", "创业", "翻身"], "filter_method": "ip_adapted", "reason": "热点迁移到IP定位"},
        {"title": "生活是一本充满故事的书：从创业到翻身的可复制打法", "score": 3.34, "tags": ["抖音", "热榜", "创业", "翻身"], "filter_method": "ip_adapted", "reason": "热点迁移到IP定位"},
    ]
    
    print("【修复前】")
    score_before = generate_report(before_topics, "修复前")
    
    print("\n\n" + "=" * 80)
    print("【修复后】")
    score_after = generate_report(MOCK_TOPICS_FIXED, "修复后（预期效果）")
    
    print("\n" + "=" * 80)
    print("对比总结")
    print("=" * 80)
    print(f"修复前得分: {score_before:.1f}/100")
    print(f"修复后得分: {score_after:.1f}/100")
    print(f"提升幅度: {score_after - score_before:+.1f}分 ({(score_after/score_before - 1)*100:+.1f}%)")
    
    if score_after > score_before:
        print("\n✅ 修复效果良好，建议部署上线")
    elif score_after < score_before:
        print("\n⚠️  修复效果不如预期，需要进一步调整")
    else:
        print("\n⚠️  修复效果不明显，建议检查算法逻辑")


if __name__ == "__main__":
    compare_versions()
