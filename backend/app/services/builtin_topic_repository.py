"""
内置爆款选题库 - 作为兜底数据源
按IP和内容类型组织的高质量选题
"""

from typing import List, Dict, Any, Optional
import random

# 小敏IP内置爆款选题库
XIAOMIN_BUILTIN_TOPICS = {
    "money": [  # 搞钱方法论 40%
        {
            "title": "2000块启动资金，我是如何做到月入3万的",
            "tags": ["低成本创业", "宝妈副业", "月入3万"],
            "score": 4.95,
            "reason": "内置爆款：低成本高回报典型案例",
            "viral_elements": ["cost", "top", "contrast"],
        },
        {
            "title": "宝妈摆摊第30天，终于突破日入1000",
            "tags": ["宝妈创业", "摆摊", "日入1000"],
            "score": 4.90,
            "reason": "内置爆款：真实成长数据",
            "viral_elements": ["crowd", "top"],
        },
        {
            "title": "不做伸手党：一个宝妈的私房创业实录",
            "tags": ["宝妈", "私房", "创业实录"],
            "score": 4.88,
            "reason": "内置爆款：情感+搞钱双驱动",
            "viral_elements": ["nostalgia", "contrast"],
        },
        {
            "title": "从负债10万到月入5万，我只用了这一招",
            "tags": ["负债翻身", "月入5万", "商业思维"],
            "score": 4.92,
            "reason": "内置爆款：负债逆袭经典模板",
            "viral_elements": ["worst", "contrast", "weird"],
        },
        {
            "title": "私域变现的真相：90%的人都做错了这一步",
            "tags": ["私域", "变现", "避坑"],
            "score": 4.85,
            "reason": "内置爆款：揭秘类高互动",
            "viral_elements": ["worst", "weird"],
        },
        {
            "title": "摆摊选址的3个秘诀，学会了收入翻3倍",
            "tags": ["摆摊", "选址", "收入翻倍"],
            "score": 4.82,
            "reason": "内置爆款：方法论干货",
            "viral_elements": ["top", "cost"],
        },
        {
            "title": "从0到月入过万：新手宝妈的创业避坑指南",
            "tags": ["新手", "宝妈", "避坑", "月入过万"],
            "score": 4.80,
            "reason": "内置爆款：新手友好型",
            "viral_elements": ["worst", "cost"],
        },
        {
            "title": "副业收入超过主业后，我辞职了",
            "tags": ["副业", "辞职", "收入"],
            "score": 4.87,
            "reason": "内置爆款：副业转正经典叙事",
            "viral_elements": ["contrast", "hormone"],
        },
    ],
    "emotion": [  # 情感共情 30%
        {
            "title": "老公说我不务正业，现在月入2万他闭嘴了",
            "tags": ["宝妈", "创业", "夫妻", "打脸"],
            "score": 4.93,
            "reason": "内置爆款：夫妻冲突+打脸剧情",
            "viral_elements": ["contrast", "hormone"],
        },
        {
            "title": "从全职妈妈到家庭支柱，我花了6个月",
            "tags": ["全职妈妈", "家庭支柱", "女性独立"],
            "score": 4.89,
            "reason": "内置爆款：身份转变情感共鸣",
            "viral_elements": ["nostalgia", "contrast"],
        },
        {
            "title": "婆婆说我带娃不赚钱，现在我月入3万她闭嘴了",
            "tags": ["婆媳", "带娃", "月入3万"],
            "score": 4.91,
            "reason": "内置爆款：婆媳冲突经典",
            "viral_elements": ["contrast", "hormone"],
        },
        {
            "title": "32岁离婚带俩娃，我是怎么靠自己走出低谷的",
            "tags": ["离婚", "带娃", "逆袭", "低谷"],
            "score": 4.94,
            "reason": "内置爆款：离婚逆袭高共鸣",
            "viral_elements": ["worst", "nostalgia", "contrast"],
        },
        {
            "title": "婚姻不是避风港：这个宝妈用创业找回了自己",
            "tags": ["婚姻", "宝妈", "创业", "独立"],
            "score": 4.86,
            "reason": "内置爆款：婚姻+独立话题",
            "viral_elements": ["nostalgia", "contrast"],
        },
        {
            "title": "当妈妈后我才明白：经济独立比啥都重要",
            "tags": ["宝妈", "经济独立", "女性成长"],
            "score": 4.84,
            "reason": "内置爆款： motherhood+独立",
            "viral_elements": ["nostalgia", "contrast"],
        },
    ],
    "skill": [  # 技术展示 20%
        {
            "title": "这个馒头配方我练了3年，今天免费分享",
            "tags": ["馒头", "配方", "教学", "免费"],
            "score": 4.88,
            "reason": "内置爆款：干货利他型",
            "viral_elements": ["cost", "top"],
        },
        {
            "title": "私房爆款的秘密：从揉面到造型的完整教程",
            "tags": ["私房", "爆款", "教程", "揉面", "造型"],
            "score": 4.85,
            "reason": "内置爆款：完整教程类",
            "viral_elements": ["top", "cost"],
        },
        {
            "title": "新手做馒头总是失败？这3个细节要注意",
            "tags": ["新手", "馒头", "失败", "技巧"],
            "score": 4.82,
            "reason": "内置爆款：问题解决型",
            "viral_elements": ["worst", "cost"],
        },
        {
            "title": "2000元起步：她用一手馒头绝活做到月入5万",
            "tags": ["低成本", "馒头", "绝活", "月入5万"],
            "score": 4.90,
            "reason": "内置爆款：技能+变现双驱动",
            "viral_elements": ["cost", "top", "contrast"],
        },
        {
            "title": "从厨房到台前：一个宝妈的手艺变现之路",
            "tags": ["宝妈", "手艺", "变现"],
            "score": 4.83,
            "reason": "内置爆款：技能转型故事",
            "viral_elements": ["nostalgia", "contrast"],
        },
    ],
    "life": [  # 美好生活 10%
        {
            "title": "创业后的我，终于活成了自己想要的样子",
            "tags": ["创业", "女性", "精致生活"],
            "score": 4.80,
            "reason": "内置爆款：生活方式展示",
            "viral_elements": ["nostalgia", "hormone"],
        },
        {
            "title": "又美又飒：创业宝妈的精致日常",
            "tags": ["宝妈", "创业", "精致", "又美又飒"],
            "score": 4.78,
            "reason": "内置爆款：人设展示型",
            "viral_elements": ["hormone"],
        },
        {
            "title": "左手事业右手生活：这个宝妈把日子过成了诗",
            "tags": ["宝妈", "事业", "生活", "品质"],
            "score": 4.76,
            "reason": "内置爆款：工作生活平衡",
            "viral_elements": ["nostalgia", "hormone"],
        },
    ],
}

# 通用内置选题（其他IP使用）
GENERIC_BUILTIN_TOPICS = {
    "money": [
        {"title": "月入过万的秘密：这个方法90%的人都不知道", "tags": ["赚钱", "副业"], "score": 4.8},
        {"title": "从0到月入3万：普通人的可复制路径", "tags": ["创业", "变现"], "score": 4.75},
        {"title": "副业收入超过主业，我做对了什么", "tags": ["副业", "收入"], "score": 4.7},
    ],
    "emotion": [
        {"title": "成年人最大的体面：拥有说不的能力", "tags": ["成长", "独立"], "score": 4.75},
        {"title": "30岁以后我才明白的10个道理", "tags": ["成长", "感悟"], "score": 4.7},
    ],
    "skill": [
        {"title": "这个技巧我练了100遍，今天分享给你", "tags": ["技巧", "教学"], "score": 4.7},
        {"title": "新手入门：从0开始的完整教程", "tags": ["新手", "教程"], "score": 4.65},
    ],
    "life": [
        {"title": "认真生活的人，生活也会认真对待你", "tags": ["生活", "态度"], "score": 4.6},
    ],
}


def get_builtin_topics(
    ip_id: str,
    content_type: Optional[str] = None,
    limit: int = 12,
    shuffle: bool = True
) -> List[Dict[str, Any]]:
    """
    获取内置爆款选题
    
    Args:
        ip_id: IP ID
        content_type: 内容类型筛选 (money/emotion/skill/life)，None表示全部
        limit: 返回数量
        shuffle: 是否打乱顺序
        
    Returns:
        选题列表
    """
    # 获取对应IP的选题库
    if ip_id == "xiaomin1":
        topics_db = XIAOMIN_BUILTIN_TOPICS
    else:
        topics_db = GENERIC_BUILTIN_TOPICS
    
    result = []
    
    # 如果指定了内容类型，只返回该类型
    if content_type and content_type in topics_db:
        result = [dict(t, content_type=content_type) for t in topics_db[content_type]]
    else:
        # 按4-3-2-1比例分配
        allocation = {"money": 0.4, "emotion": 0.3, "skill": 0.2, "life": 0.1}
        for ctype, ratio in allocation.items():
            if ctype in topics_db:
                count = max(1, int(limit * ratio))
                topics = [dict(t, content_type=ctype) for t in topics_db[ctype]]
                result.extend(topics[:count])
    
    # 添加通用字段
    for i, topic in enumerate(result):
        topic["id"] = f"builtin_{topic.get('content_type', 'other')}_{i}"
        topic["source"] = "builtin"
        topic["estimatedViews"] = f"{int(topic.get('score', 4) * 5)}万+"
        topic["estimatedCompletion"] = int(topic.get('score', 4) * 20)
    
    # 打乱顺序
    if shuffle:
        random.shuffle(result)
    
    return result[:limit]


def get_topics_by_matrix(ip_id: str, limit: int = 12) -> List[Dict[str, Any]]:
    """
    按内容矩阵比例获取选题
    40% money + 30% emotion + 20% skill + 10% life
    
    Args:
        ip_id: IP ID
        limit: 总数限制
        
    Returns:
        按比例分配的选题列表
    """
    matrix = {
        "money": int(limit * 0.4),
        "emotion": int(limit * 0.3),
        "skill": int(limit * 0.2),
        "life": max(1, limit - int(limit * 0.4) - int(limit * 0.3) - int(limit * 0.2)),
    }
    
    result = []
    for content_type, count in matrix.items():
        topics = get_builtin_topics(ip_id, content_type, count, shuffle=True)
        result.extend(topics)
    
    # 打乱顺序
    random.shuffle(result)
    return result[:limit]


def get_emergency_topics(ip_id: str = "xiaomin1", limit: int = 12) -> List[Dict[str, Any]]:
    """
    获取紧急兜底选题（当所有数据源都失败时使用）
    返回最优质的精选选题
    
    Args:
        ip_id: IP ID
        limit: 返回数量
        
    Returns:
        精选选题列表
    """
    # 获取所有类型
    all_topics = []
    for content_type in ["money", "emotion", "skill", "life"]:
        topics = get_builtin_topics(ip_id, content_type, limit=100, shuffle=False)
        all_topics.extend(topics)
    
    # 按分数排序，取最高分
    all_topics.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # 打乱前limit个
    top_topics = all_topics[:limit]
    random.shuffle(top_topics)
    
    return top_topics
