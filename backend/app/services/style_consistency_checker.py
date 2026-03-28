"""
IP风格一致性检查服务
检测生成内容是否保持IP特征：口头禅、词汇、语气
"""
from typing import Any, Dict, List, Optional
import re


def check_style_consistency(
    content: str,
    ip_style: Dict[str, Any],
) -> Dict[str, Any]:
    """
    检查内容与IP风格的一致性
    
    Args:
        content: 生成的内容
        ip_style: IP风格特征
    
    Returns:
        一致性检查结果
    """
    # Handle None or empty content
    if not content:
        return {
            "score": 0.5,
            "issues": ["No content generated"],
            "details": {}
        }
    
    issues = []
    score = 1.0
    
    # 1. 检查口头禅使用
    catchphrases = ip_style.get("catchphrases", "")
    if catchphrases:
        cp_list = [c.strip() for c in catchphrases.split(",") if c.strip()]
        used_catchphrases = []
        missing_catchphrases = []
        
        for cp in cp_list:
            if cp in content:
                used_catchphrases.append(cp)
            else:
                missing_catchphrases.append(cp)
        
        # 口头禅覆盖率
        if cp_list:
            coverage = len(used_catchphrases) / len(cp_list)
            if coverage < 0.3:
                issues.append(f"口头禅使用不足（{len(used_catchphrases)}/{len(cp_list)}）")
                score -= 0.2
    
    # 2. 检查关键词使用
    vocabulary = ip_style.get("vocabulary", "")
    if vocabulary:
        vocab_list = [v.strip() for v in vocabulary.split(",") if v.strip()]
        used_vocab = []
        
        for v in vocab_list:
            if v in content:
                used_vocab.append(v)
        
        # 词汇覆盖率
        if vocab_list:
            coverage = len(used_vocab) / len(vocab_list)
            if coverage < 0.2:
                issues.append(f"专业词汇使用不足")
                score -= 0.15
    
    # 3. 检查人称一致性
    tone = ip_style.get("tone", "")
    first_person_indicators = ["我", "我们", "我的"]
    second_person_indicators = ["你", "你们", "你的"]
    
    has_first = any(ip in content for ip in first_person_indicators)
    has_second = any(ip in content for ip in second_person_indicators)
    
    if "亲切" in tone or "温暖" in tone:
        # 应该有多重人称互动
        if not (has_first and has_second):
            issues.append("人称互动不足（应同时使用第一人称和第二人称）")
            score -= 0.1
    
    # 4. 检查句子长度（短句更适合短视频）
    sentences = re.split(r'[。！？]', content)
    avg_sentence_len = sum(len(s) for s in sentences) / max(len(sentences), 1)
    
    if avg_sentence_len > 40:
        issues.append(f"句子偏长（平均{avg_sentence_len:.0f}字，建议≤30字）")
        score -= 0.1
    
    # 5. 检查标点（短视频需要更多感叹号和问号）
    exclamation_count = content.count("！")
    question_count = content.count("？")
    
    if exclamation_count + question_count < 2:
        issues.append("情感标点使用不足")
        score -= 0.05
    
    # 确保分数在0-1范围
    score = max(0.0, min(1.0, score))
    
    return {
        "score": score,
        "issues": issues,
        "details": {
            "used_catchphrases": used_catchphrases if 'used_catchphrases' in dir() else [],
            "avg_sentence_length": round(avg_sentence_len, 1),
            "exclamation_count": exclamation_count,
            "question_count": question_count,
        }
    }


def recommend_style_improvements(
    content: str,
    ip_style: Dict[str, Any],
    check_result: Dict[str, Any]
) -> List[str]:
    """
    基于风格检查结果给出改进建议
    """
    suggestions = []
    
    issues = check_result.get("issues", [])
    
    if any("口头禅" in issue for issue in issues):
        catchphrases = ip_style.get("catchphrases", "")
        if catchphrases:
            suggestions.append(f"建议在内容中融入口头禅，如：{catchphrases.split(',')[0]}")
    
    if any("专业词汇" in issue for issue in issues):
        suggestions.append("增加专业术语的使用，提升可信度")
    
    if any("人称" in issue for issue in issues):
        suggestions.append('增加人称互动，使用"你"和"我"的对话感')
    
    if any("句子" in issue for issue in issues):
        suggestions.append("将长句拆分为短句，每句不超过30字")
    
    if any("情感标点" in issue for issue in issues):
        suggestions.append("增加感叹号和问号，提升情绪感染力")
    
    return suggestions