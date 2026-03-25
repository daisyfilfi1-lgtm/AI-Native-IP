"""
IP风格建模服务
从历史素材中提取IP风格特征，应用于内容生成
"""
from typing import Any, Dict, List, Optional
from collections import Counter
import re
from pydantic import BaseModel

from app.services.ai_client import chat, get_ai_config


# ==================== 风格特征模型 ====================

class IPStyleProfile(BaseModel):
    """IP风格画像"""
    ip_id: str
    vocabulary: List[str]           # 高频词汇
    sentence_patterns: List[str]   # 句式特征
    emotion_curve: str              # 情感曲线
    catchphrases: List[str]        # 口头禅
    tone: str                       # 语气特征
    topics: List[str]               # 常聊话题
    length_preference: str          # 长度偏好
    format_preference: str          # 格式偏好
    
    # 扩展特征
    humor_style: Optional[str] = None      # 幽默风格
    formality: Optional[float] = 0.5        # 正式程度 0-1
    emotion_density: Optional[float] = 0.5  # 情感密度 0-1
    self_intro: Optional[str] = None
    forbidden_self_names: Optional[List[str]] = None


class StyleExtractor:
    """
    风格特征提取器
    从素材中自动提取IP风格特征
    """
    
    def __init__(self):
        self.cfg = get_ai_config()
    
    def extract(self, assets: List[Dict]) -> IPStyleProfile:
        """
        从素材列表提取风格特征
        
        Args:
            assets: 素材列表，每项包含 content, type 等
        
        Returns:
            IPStyleProfile: 完整的风格画像
        """
        texts = [a.get("content", "") for a in assets if a.get("content")]
        
        # 1. 提取词汇特征
        vocabulary = self._extract_vocabulary(texts)
        
        # 2. 提取句式特征
        sentence_patterns = self._extract_sentence_patterns(texts)
        
        # 3. 提取口头禅
        catchphrases = self._extract_catchphrases(texts)
        
        # 4. LLM分析情感和语气
        tone, emotion_curve = self._analyze_tone(texts)
        
        # 5. 提取常聊话题
        topics = self._extract_topics(texts)
        
        # 6. 长度和格式偏好
        length_pref, format_pref = self._analyze_preferences(texts)
        
        return IPStyleProfile(
            ip_id="",  # 外部传入
            vocabulary=vocabulary,
            sentence_patterns=sentence_patterns,
            emotion_curve=emotion_curve,
            catchphrases=catchphrases,
            tone=tone,
            topics=topics,
            length_preference=length_pref,
            format_preference=format_pref,
        )
    
    def _extract_vocabulary(self, texts: List[str]) -> List[str]:
        """提取高频词汇"""
        # 简单词频统计（可升级为TF-IDF）
        words = []
        for text in texts:
            # 提取中文词
            chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
            words.extend(chinese_words)
        
        # 过滤停用词
        stopwords = {"的", "是", "了", "在", "和", "与", "或", "以及", "但是", "所以", "因为", "如果"}
        words = [w for w in words if w not in stopwords and len(w) >= 2]
        
        # 取top 50
        counter = Counter(words)
        return [w for w, _ in counter.most_common(50)]
    
    def _extract_sentence_patterns(self, texts: List[str]) -> List[str]:
        """提取句式特征"""
        patterns = []
        
        for text in texts:
            # 问句比例
            if "？" in text or "?" in text:
                patterns.append("喜欢用问句")
            
            # 感叹句
            if "！" in text:
                patterns.append("喜欢用感叹")
            
            # 短句风格
            sentences = re.split(r'[。！？]', text)
            avg_len = sum(len(s) for s in sentences) / max(len(sentences), 1)
            if avg_len < 20:
                patterns.append("短句为主")
            elif avg_len > 40:
                patterns.append("长句为主")
        
        # 去重
        return list(set(patterns))[:10]
    
    def _extract_catchphrases(self, texts: List[str]) -> List[str]:
        """提取口头禅"""
        # 常见模式：句首/句尾重复词
        catchphrases = []
        
        for text in texts[:20]:  # 样本限制
            sentences = text.split('。')
            for s in sentences[:3]:  # 每篇取前3句
                s = s.strip()
                if len(s) > 0 and len(s) < 15:
                    # 查找可能的短语
                    if s.startswith("其实") or s.startswith("真的"):
                        catchphrases.append(s[:10])
        
        # LLM辅助提取更准
        prompt = f"""从以下文本中提取IP的口头禅或常用表达（3-5个）：

{texts[:5]}

直接输出列表，不要解释。"""
        
        try:
            result = chat(
                model=self.cfg.get("llm_model", "deepseek-chat"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            # 解析结果
            phrases = [p.strip().strip("- ").strip() for p in result.split("\n") if p.strip()]
            catchphrases.extend(phrases[:5])
        except:
            pass
        
        return list(set(catchphrases))[:10]
    
    def _analyze_tone(self, texts: List[str]) -> tuple:
        """分析语气和情感"""
        sample = "\n".join(texts[:10])
        
        prompt = f"""分析以下内容的语气和情感特征：

{sample[:2000]}

输出JSON格式：
{{
  "tone": "语气描述（如：亲切专业、幽默风趣、严肃认真）",
  "emotion_curve": "情感曲线描述（如：平稳起伏、先抑后扬）"
}}"""
        
        try:
            result = chat(
                model=self.cfg.get("llm_model", "deepseek-chat"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            
            import json
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            data = json.loads(result.strip())
            return data.get("tone", "亲切"), data.get("emotion_curve", "平稳")
        except:
            return "亲切专业", "平稳"
    
    def _extract_topics(self, texts: List[str]) -> List[str]:
        """提取常聊话题"""
        prompt = f"""从以下文本中提取IP常聊的话题（5-8个）：

{texts[:10]}

直接输出列表。"""
        
        try:
            result = chat(
                model=self.cfg.get("llm_model", "deepseek-chat"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            topics = [t.strip().strip("- ").strip() for t in result.split("\n") if t.strip()]
            return topics[:10]
        except:
            return []
    
    def _analyze_preferences(self, texts: List[str]) -> tuple:
        """分析长度和格式偏好"""
        lengths = []
        formats = []
        
        for text in texts:
            lengths.append(len(text))
            if "：" in text or "：" in text:
                formats.append("问答式")
            if "\n" in text:
                formats.append("分段式")
            if len(text) < 100:
                formats.append("短文本")
        
        avg_len = sum(lengths) / max(len(lengths), 1)
        
        if avg_len < 200:
            length_pref = "短篇（100-200字）"
        elif avg_len < 500:
            length_pref = "中篇（200-500字）"
        else:
            length_pref = "长篇（500+字）"
        
        format_pref = Counter(formats).most_common(1)[0][0] if formats else "自然段落"
        
        return length_pref, format_pref


class StyleTransfer:
    """
    风格迁移器
    将风格特征应用于内容生成
    """
    
    def __init__(self, style_profile: IPStyleProfile):
        self.profile = style_profile
        self.cfg = get_ai_config()
    
    def apply(self, content: str) -> str:
        """
        将IP风格应用于内容
        
        Args:
            content: 原始内容/主题
        
        Returns:
            str: 带IP风格的内容
        """
        prompt = f"""你是一个资深的{self.profile.tone}。

## 你的特征
- 说话风格: {self.profile.tone}
- 常用词汇: {', '.join(self.profile.vocabulary[:10])}
- 口头禅: {', '.join(self.profile.catchphrases[:5])}
- 句式偏好: {', '.join(self.profile.sentence_patterns[:3])}
- 长度偏好: {self.profile.length_preference}

## 要表达的内容
{content}

请用你的风格重新表达，保持原意但更具个人特色。"""
        
        result = chat(
            model=self.cfg.get("llm_model", "deepseek-chat"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        
        return result
    
    def generate(self, topic: str) -> str:
        """
        基于风格生成内容
        
        Args:
            topic: 话题/主题
        
        Returns:
            str: 生成的内容
        """
        prompt = f"""你是一个{self.profile.tone}。

## 风格特征
- 常用词汇: {', '.join(self.profile.vocabulary[:15])}
- 口头禅: {', '.join(self.profile.catchphrases[:5])}
- 句式: {', '.join(self.profile.sentence_patterns[:3])}
- 长度: {self.profile.length_preference}
- 格式: {self.profile.format_preference}

## 话题
{topic}

请根据你的风格生成内容。"""
        
        result = chat(
            model=self.cfg.get("llm_model", "deepseek-chat"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        
        return result


# ==================== 便捷函数 ====================

def extract_style_from_assets(assets: List[Dict], ip_id: str) -> IPStyleProfile:
    """从素材提取风格"""
    extractor = StyleExtractor()
    profile = extractor.extract(assets)
    profile.ip_id = ip_id
    return profile


def apply_style(content: str, style_profile: IPStyleProfile) -> str:
    """应用风格到内容"""
    transfer = StyleTransfer(style_profile)
    return transfer.apply(content)


def generate_with_style(topic: str, style_profile: IPStyleProfile) -> str:
    """带风格生成内容"""
    transfer = StyleTransfer(style_profile)
    return transfer.generate(topic)
