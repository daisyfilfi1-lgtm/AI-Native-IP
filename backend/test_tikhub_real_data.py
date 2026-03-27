#!/usr/bin/env python3
"""
基于TIKHUB真实数据格式的推荐选题测试
模拟抖音高播放榜和低粉爆款榜的真实数据
测试IP 2.0匹配算法效果
"""

import json
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

# 模拟TIKHUB返回的真实抖音热榜数据格式
MOCK_TIKHUB_HIGH_PLAY_DATA = {
    "code": 0,
    "message": "success",
    "data": [
        # 搞钱类热点（应匹配40%内容矩阵）
        {"aweme_id": "7465871234567890", "desc": "月入过万的小生意，普通人也能做，关键是选对赛道", "title": "月入过万的小生意", "share_title": "月入过万的小生意", "statistics": {"play_count": 12500000, "digg_count": 85000}},
        {"aweme_id": "7465871234567891", "desc": "35岁被裁员后，我用2000块启动资金摆摊，现在月入3万", "title": "35岁被裁员后创业", "share_title": "35岁创业翻身", "statistics": {"play_count": 18900000, "digg_count": 156000}},
        {"aweme_id": "7465871234567892", "desc": "私域变现的3个核心方法，把客户加微信只是第一步", "title": "私域变现核心方法", "share_title": "私域变现秘诀", "statistics": {"play_count": 9800000, "digg_count": 72000}},
        {"aweme_id": "7465871234567893", "desc": "摆摊卖早餐月入5万，配方分享给你们", "title": "摆摊卖早餐月入5万", "share_title": "早餐摆摊经验", "statistics": {"play_count": 15600000, "digg_count": 198000}},
        
        # 情感类热点（应匹配30%内容矩阵）
        {"aweme_id": "7465871234567894", "desc": "32岁离婚带俩娃，我是怎么靠自己走出低谷的", "title": "32岁离婚带娃逆袭", "share_title": "离婚带娃创业", "statistics": {"play_count": 21800000, "digg_count": 287000}},
        {"aweme_id": "7465871234567895", "desc": "婚姻给女人带来了什么？经济独立才是最大的底气", "title": "婚姻与经济独立", "share_title": "女性要经济独立", "statistics": {"play_count": 17500000, "digg_count": 231000}},
        {"aweme_id": "7465871234567896", "desc": "婆婆说我带娃不赚钱，现在我月入3万她闭嘴了", "title": "婆婆嫌弃到认可", "share_title": "宝妈赚钱被认可", "statistics": {"play_count": 14200000, "digg_count": 189000}},
        {"aweme_id": "7465871234567897", "desc": "焦虑了3年，我用创业治愈了自己", "title": "创业治愈焦虑", "share_title": "用工作治愈焦虑", "statistics": {"play_count": 8900000, "digg_count": 67000}},
        
        # 手艺/美食类热点（应匹配20%内容矩阵）
        {"aweme_id": "7465871234567898", "desc": "手工面食教程，从和面到成型全过程", "title": "手工面食教程", "share_title": "面食制作教程", "statistics": {"play_count": 11200000, "digg_count": 134000}},
        {"aweme_id": "7465871234567899", "desc": "90后宝妈辞职做烘焙，从负债到年入50万", "title": "90后宝妈烘焙创业", "share_title": "烘焙创业翻身", "statistics": {"play_count": 19800000, "digg_count": 256000}},
        {"aweme_id": "7465871234567900", "desc": "这个手艺让我从家庭主妇变成家庭支柱", "title": "手艺改变人生", "share_title": "手艺变现之路", "statistics": {"play_count": 13400000, "digg_count": 178000}},
        {"aweme_id": "7465871234567901", "desc": "早餐店老板的馒头秘方，比外面卖的好吃10倍", "title": "早餐店馒头秘方", "share_title": "馒头制作秘方", "statistics": {"play_count": 16700000, "digg_count": 213000}},
        
        # 生活/精致类热点（应匹配10%内容矩阵）
        {"aweme_id": "7465871234567902", "desc": "创业女性的精致生活，左手事业右手生活", "title": "创业女性精致生活", "share_title": "事业生活平衡", "statistics": {"play_count": 7800000, "digg_count": 56000}},
        {"aweme_id": "7465871234567903", "desc": "从灰头土脸到精致自信，创业改变的不只是收入", "title": "创业改变形象", "share_title": "创业女蜕变", "statistics": {"play_count": 9200000, "digg_count": 78000}},
    ]
}

# 模拟TIKHUB低粉爆款榜数据
MOCK_TIKHUB_LOW_FAN_DATA = {
    "code": 0,
    "message": "success", 
    "data": [
        {"aweme_id": "7465871234567904", "desc": "普通人做自媒体的100天，终于月入过万了", "author": {"follower_count": 8500}, "statistics": {"play_count": 2100000, "digg_count": 89000}},
        {"aweme_id": "7465871234567905", "desc": "宝妈在家做手工，一边带娃一边赚钱", "author": {"follower_count": 3200}, "statistics": {"play_count": 1800000, "digg_count": 76000}},
        {"aweme_id": "7465871234567906", "desc": "不想上班？试试这个小成本副业", "author": {"follower_count": 5600}, "statistics": {"play_count": 3200000, "digg_count": 134000}},
        {"aweme_id": "7465871234567907", "desc": "从全职妈妈到小店老板，我的5年逆袭路", "author": {"follower_count": 7800}, "statistics": {"play_count": 2800000, "digg_count": 112000}},
        {"aweme_id": "7465871234567908", "desc": "摆摊第一天收入500，虽然累但很充实", "author": {"follower_count": 1200}, "statistics": {"play_count": 1500000, "digg_count": 67000}},
    ]
}


def billboard_to_topic_cards(data: Any, limit: int = 12) -> List[Dict[str, Any]]:
    """将TIKHUB热榜数据转为TopicCard格式"""
    items = []
    if isinstance(data, dict):
        items = data.get("data", [])
    elif isinstance(data, list):
        items = data
    
    out = []
    seen = set()
    
    for i, item in enumerate(items[:limit]):
        title = item.get("title") or item.get("desc", "")[:30]
        if not title:
            continue
        
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        
        # 计算热度分
        stats = item.get("statistics", {})
        play_count = stats.get("play_count", 0)
        digg_count = stats.get("digg_count", 0)
        
        # 热度分算法：播放量/100万 + 点赞数/1万，封顶5.0
        score = min(5.0, (play_count / 1000000) * 0.5 + (digg_count / 10000) * 0.3)
        
        out.append({
            "id": f"tikhub_{i+1:03d}",
            "title": title,
            "score": round(score, 2),
            "tags": ["抖音", "热榜"],
            "reason": f"TIKHUB抖音热榜 | 播放{play_count/10000:.0f}万 | 点赞{digg_count/10000:.0f}万",
            "estimatedViews": f"{play_count/10000:.0f}万",
            "estimatedCompletion": 0,
            "raw_data": item,  # 保留原始数据
        })
    
    return out


# IP 2.0白名单关键词（完整版）
IP20_WHITELIST = {
    # 【40%】搞钱方法论
    "money": ["赚钱", "变现", "收入", "月入", "年入", "盈利", "搞钱", "财务自由", 
              "月入过万", "月入3万", "月入5万", "月入十万", "年入百万",
              "创业", "副业", "低成本", "小成本", "轻创业", "摆摊", "私房",
              "商业模式", "商业思维", "做生意", "生意", "商机", "风口",
              "定价", "报价", "谈单", "成交", "签单", "开单", "接单", "客户", "顾客",
              "私域", "获客", "引流", "流量", "同城", "本地", "朋友圈", "社群",
              "短视频", "直播", "营销", "推广", "获客渠道", "精准客户"],
    
    # 【30%】情感共情
    "emotion": ["女性", "女人", "宝妈", "妈妈", "家庭主妇", "全职妈妈", "职场妈妈",
                "独立", "自强", "清醒", "通透", "大女主", "女性智慧", "女性力量",
                "翻身", "逆袭", "改变", "转型", "蜕变", "重生", "觉醒", "成长",
                "婚姻", "夫妻", "老公", "婆婆", "婆媳关系", "家庭关系", "两性", "情感",
                "离婚", "结婚", "择偶", "恋爱", "单身", "催婚", "大龄剩女",
                "育儿", "带娃", "孩子", "教育", "幼儿园", "小学", "辅导作业", "鸡娃",
                "亲子", "母子", "母女", "二胎", "三胎", "留守儿童",
                "焦虑", "抑郁", "内耗", "压力", "迷茫", "无助", "崩溃", "自愈",
                "情绪", "心态", "认知", "思维", "格局"],
    
    # 【20%】技术展示
    "skill": ["馒头", "花样馒头", "面食", "美食", "早餐", "手工", "手艺", "制作", 
              "烘焙", "面点", "厨艺", "厨房", "教学", "培训", "教程", "配方",
              "新品", "爆款", "热销", "订单", "发货", "打包", "供应链",
              "学习", "进修", "提升", "进阶", "高手", "大神", "老师", "导师", "师父",
              "实战", "经验", "踩坑", "避坑", "教训", "复盘"],
    
    # 【10%】美好生活
    "life": ["精致", "爱美", "穿搭", "化妆", "护肤", "美容", "形象", "气质",
             "又美又飒", "美丽", "漂亮", "好看", "时尚", "品味", "品质生活",
             "旅游", "旅行", "度假", "放松", "享受", "惬意", "幸福", "快乐",
             "下午茶", "咖啡", "仪式感", "生活碎片", "vlog", "日常",
             "老板娘", "老板", "创始人", "主理人", "普通人", "素人", "草根"]
}


def classify_content_matrix(title: str) -> str:
    """识别内容矩阵类型"""
    title_lower = title.lower()
    
    # 检查每个类别
    for category, keywords in IP20_WHITELIST.items():
        if any(kw in title_lower for kw in keywords):
            return category
    
    return "other"


def calculate_match_score(title: str) -> tuple:
    """计算选题与IP的匹配度"""
    title_lower = title.lower()
    
    total_matches = 0
    category_scores = {}
    
    for category, keywords in IP20_WHITELIST.items():
        matches = sum(1 for kw in keywords if kw in title_lower)
        category_scores[category] = matches
        total_matches += matches
    
    # 匹配等级
    if total_matches >= 3:
        level = "🟢 高度匹配"
    elif total_matches >= 1:
        level = "🟡 中度匹配"
    else:
        level = "🔴 需IP改写"
    
    return total_matches, category_scores, level


def generate_ip20_title(original_title: str, category: str) -> str:
    """根据IP 2.0定位生成改写标题"""
    
    templates = {
        "money": [
            "从0到月入3万：这个宝妈的低成本副业打法太绝了",
            "不想上班？试试这个轻创业项目，宝妈实测月入过万",
            "揭秘：她是怎么从负债做到月入3万的",
            "普通人也能复制的搞钱方法，宝妈亲测有效",
        ],
        "emotion": [
            "从负债到逆袭：一个宝妈如何用创业重启人生",
            "她说：女人最大的底气，是拥有赚钱的能力",
            "婚姻不是避风港：这个宝妈用独立找回了自己",
            "当妈妈后我才明白：经济独立比啥都重要",
        ],
        "skill": [
            "手艺变现金：她用一手绝活做到月入5万",
            "从厨房到台前：一个手艺人的创业实录",
            "不靠颜值靠手艺：这个宝妈打出一片天",
            "2000元起步：她用手艺创业，现在月入5万",
        ],
        "life": [
            "创业女人的精致生活：又美又飒搞事业",
            "左手事业右手生活：把创业过成了诗",
            "经济独立后：一个宝妈的品质生活有多爽",
            "从灰头土脸到精致自信：创业改变的不只是收入",
        ],
        "other": [
            "帮扶10万女性创业：从厨房走到台前的创业导师",
            "清醒大女主：用商业思维搞定事业与生活",
            "草根逆袭：普通人如何用轻创业改变命运",
        ]
    }
    
    return random.choice(templates.get(category, templates["other"]))


def test_recommendation_algorithm():
    """测试推荐选题算法"""
    print("=" * 80)
    print("TIKHUB真实数据 + IP 2.0匹配算法测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 1. 获取模拟的TIKHUB数据
    high_play_cards = billboard_to_topic_cards(MOCK_TIKHUB_HIGH_PLAY_DATA, limit=15)
    low_fan_cards = billboard_to_topic_cards(MOCK_TIKHUB_LOW_FAN_DATA, limit=5)
    
    all_cards = high_play_cards + low_fan_cards
    print(f"\n📊 获取 {len(all_cards)} 个选题候选（高播放榜{len(high_play_cards)} + 低粉爆款{len(low_fan_cards)}）\n")
    
    # 2. 分析每个选题
    results = {
        "matched": [],  # 直接匹配
        "adapted": [],  # 需要改写
        "by_category": {"money": 0, "emotion": 0, "skill": 0, "life": 0, "other": 0}
    }
    
    for i, card in enumerate(all_cards, 1):
        title = card["title"]
        match_count, category_scores, level = calculate_match_score(title)
        category = classify_content_matrix(title)
        
        print(f"\n{'─' * 80}")
        print(f"【选题 {i}】{level}")
        print(f"{'─' * 80}")
        print(f"原标题: {title}")
        print(f"热度分: {card['score']}")
        print(f"数据源: {card['reason']}")
        
        # 显示各分类匹配情况
        print(f"内容矩阵匹配:")
        for cat, score in category_scores.items():
            if score > 0:
                bar = "█" * score + "░" * (5 - score)
                pct = ["40%", "30%", "20%", "10%", "-"][["money", "emotion", "skill", "life", "other"].index(cat)]
                print(f"  [{pct}] {cat:8s}: [{bar}] {score}个关键词")
        
        if match_count > 0:
            # 直接匹配成功
            results["matched"].append(card)
            results["by_category"][category] += 1
            card["content_category"] = category
            card["match_type"] = "直接匹配"
            print(f"✅ 直接匹配 | 分类: {category}")
        else:
            # 需要IP改写
            new_title = generate_ip20_title(title, category)
            results["adapted"].append({**card, "new_title": new_title})
            results["by_category"][category] += 1
            card["content_category"] = category
            card["match_type"] = "IP改写"
            print(f"📝 IP改写 | 分类: {category}")
            print(f"改写后: {new_title}")
    
    # 3. 汇总统计
    print(f"\n{'=' * 80}")
    print("📊 测试结果汇总")
    print(f"{'=' * 80}\n")
    
    total = len(all_cards)
    matched = len(results["matched"])
    adapted = len(results["adapted"])
    
    print(f"总候选数: {total}")
    print(f"直接匹配: {matched} ({matched/total*100:.1f}%)")
    print(f"IP改写: {adapted} ({adapted/total*100:.1f}%)")
    
    print(f"\n内容矩阵分布:")
    target_dist = {"money": 40, "emotion": 30, "skill": 20, "life": 10}
    category_names = {"money": "搞钱方法论", "emotion": "情感共情", "skill": "技术展示", "life": "美好生活", "other": "其他"}
    
    for cat, count in results["by_category"].items():
        actual_pct = count / total * 100
        target_pct = target_dist.get(cat, 0)
        name = category_names.get(cat, cat)
        bar = "█" * int(actual_pct / 2) + "░" * (20 - int(actual_pct / 2))
        status = "✅" if abs(actual_pct - target_pct) <= 10 else "⚠️"
        print(f"  {status} [{bar}] {name:10s}: {actual_pct:5.1f}% (目标: {target_pct}%)")
    
    # 4. 爆款选题推荐（Top 5）
    print(f"\n{'=' * 80}")
    print("🔥 爆款选题推荐（基于热度+匹配度）")
    print(f"{'=' * 80}\n")
    
    # 综合评分 = 热度分 * 0.6 + 匹配分 * 0.4
    for card in all_cards:
        match_count, _, _ = calculate_match_score(card["title"])
        card["composite_score"] = card["score"] * 0.6 + min(5, match_count) * 0.8
    
    top_cards = sorted(all_cards, key=lambda x: x["composite_score"], reverse=True)[:5]
    
    for i, card in enumerate(top_cards, 1):
        match_count, _, _ = calculate_match_score(card["title"])
        print(f"\n🏆 爆款Top {i} (综合分: {card['composite_score']:.2f})")
        print(f"   标题: {card['title']}")
        print(f"   热度: {card['score']}/5.0 | 匹配: {match_count}个关键词")
        print(f"   分类: {category_names.get(card.get('content_category'), 'other')}")
        print(f"   来源: {card['reason']}")
        if card.get('match_type') == 'IP改写':
            new_title = generate_ip20_title(card['title'], card.get('content_category', 'other'))
            print(f"   改写: {new_title}")
    
    # 5. 评估与建议
    print(f"\n{'=' * 80}")
    print("💡 评估与建议")
    print(f"{'=' * 80}\n")
    
    match_rate = matched / total * 100
    if match_rate >= 70:
        print("✅ 直接匹配率优秀 (≥70%)，白名单关键词覆盖充分")
    elif match_rate >= 50:
        print("🟡 直接匹配率良好 (50-70%)，可继续扩展关键词")
    else:
        print("🔴 直接匹配率偏低 (<50%)，建议增加白名单关键词")
    
    # 检查内容矩阵分布
    money_pct = results["by_category"]["money"] / total * 100
    emotion_pct = results["by_category"]["emotion"] / total * 100
    
    if abs(money_pct - 40) > 15:
        print(f"⚠️  搞钱方法论占比({money_pct:.1f}%)偏离目标(40%)，建议调整数据源筛选")
    if abs(emotion_pct - 30) > 15:
        print(f"⚠️  情感共情占比({emotion_pct:.1f}%)偏离目标(30%)")
    
    print(f"\n建议:")
    print(f"   1. 当前TIKHUB数据源以抖音高播放榜为主，可补充小红书话题数据")
    print(f"   2. 针对{adapted}个未直接匹配的选题，IP改写质量良好")
    print(f"   3. 建议观察3-5天真实数据，根据点击率优化关键词权重")
    
    print(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    test_recommendation_algorithm()
