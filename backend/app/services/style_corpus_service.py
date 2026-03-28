from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.db.models import IPAsset
from app.services.vector_service import query_similar_assets


_DEFAULT_CORPUS_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "IP知识库"
    / "小敏IP_Style_Corpus_完整26条_预训练素材库.json"
)


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return re.findall(r"[\u4e00-\u9fa5]{1,}|[A-Za-z0-9_]{2,}", text.lower())


def _cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a.keys()) & set(b.keys())
    if not common:
        return 0.0
    dot = sum(a[k] * b[k] for k in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (na * nb)


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


@dataclass
class _SampleIndexItem:
    sample_id: str
    vector: Dict[str, float]
    sample: Dict[str, Any]


class StyleCorpusService:
    """IP 风格语料服务：向量检索 + 风格约束 + 对抗评分。"""

    def __init__(self, corpus_path: Optional[Path] = None):
        self.corpus_path = corpus_path or _DEFAULT_CORPUS_PATH
        self.corpus = self._load_corpus(self.corpus_path)
        self.samples = self.corpus.get("samples") or []
        self.global_constraints = self.corpus.get("global_style_constraints") or {}
        self.technical_params = self.corpus.get("technical_params") or {}
        self.quality_thresholds = (self.technical_params.get("quality_thresholds") or {})
        self._index = self._build_index(self.samples)

    @staticmethod
    @lru_cache(maxsize=4)
    def _load_corpus(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _build_index(self, samples: Sequence[Dict[str, Any]]) -> List[_SampleIndexItem]:
        items: List[_SampleIndexItem] = []
        for sample in samples:
            sid = str(sample.get("sample_id") or "").strip()
            if not sid:
                continue
            retrieval_tags = sample.get("retrieval_tags") or {}
            tokens: List[str] = []
            tokens.extend(_tokenize(str(sample.get("content_type") or "")))
            tokens.extend(_tokenize(str(sample.get("raw_topic") or "")))
            for key in ("theme_vector", "emotion_tags", "target_audience", "scene_context"):
                val = retrieval_tags.get(key)
                if isinstance(val, list):
                    for x in val:
                        tokens.extend(_tokenize(str(x)))
                elif isinstance(val, str):
                    tokens.extend(_tokenize(val))
            entities = sample.get("content_entities") or {}
            for k in ("core_topic", "pain_point", "solution", "key_concept"):
                tokens.extend(_tokenize(str(entities.get(k) or "")))
            if not tokens:
                continue
            vec: Dict[str, float] = {}
            for t in tokens:
                vec[t] = vec.get(t, 0.0) + 1.0
            items.append(_SampleIndexItem(sample_id=sid, vector=vec, sample=sample))
        return items

    def search_samples(
        self,
        *,
        topic: str,
        emotion: str = "",
        audience: str = "",
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """按主题/情绪/人群进行向量检索。"""
        q_tokens: List[str] = []
        q_tokens.extend(_tokenize(topic))
        q_tokens.extend(_tokenize(emotion))
        q_tokens.extend(_tokenize(audience))
        if not q_tokens:
            return []
        q_vec: Dict[str, float] = {}
        for t in q_tokens:
            q_vec[t] = q_vec.get(t, 0.0) + 1.0

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for item in self._index:
            sim = _cosine_similarity(q_vec, item.vector)
            if sim <= 0:
                continue
            scored.append((sim, item.sample))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[: max(1, top_k)]]

    @staticmethod
    def build_retrieval_query(*, topic: str, emotion: str = "", audience: str = "") -> str:
        parts: List[str] = []
        if topic.strip():
            parts.append(f"主题: {topic.strip()}")
        if emotion.strip():
            parts.append(f"情绪: {emotion.strip()}")
        if audience.strip():
            parts.append(f"人群: {audience.strip()}")
        return "；".join(parts)

    def search_samples_by_pgvector(
        self,
        db: Session,
        *,
        ip_id: str,
        topic: str,
        emotion: str = "",
        audience: str = "",
        top_k: int = 3,
        candidate_k: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        走现有 embedding + pgvector 架构检索 style corpus 样本。
        仅返回 metadata.source == style_corpus 的素材。
        """
        query = self.build_retrieval_query(topic=topic, emotion=emotion, audience=audience)
        if not query.strip():
            return []
        hits = query_similar_assets(db, ip_id=ip_id, query=query, top_k=max(top_k, candidate_k))
        if not hits:
            return []
        hit_ids = [str(h.get("asset_id") or "").strip() for h in hits if str(h.get("asset_id") or "").strip()]
        if not hit_ids:
            return []
        rows = (
            db.query(IPAsset)
            .filter(IPAsset.ip_id == ip_id, IPAsset.asset_id.in_(hit_ids), IPAsset.status == "active")
            .all()
        )
        row_by_id = {r.asset_id: r for r in rows}
        out: List[Dict[str, Any]] = []
        for h in hits:
            aid = str(h.get("asset_id") or "").strip()
            row = row_by_id.get(aid)
            if not row:
                continue
            meta = row.asset_meta if isinstance(row.asset_meta, dict) else {}
            if str(meta.get("source") or "") != "style_corpus":
                continue
            sample = meta.get("style_corpus_sample")
            if isinstance(sample, dict) and sample.get("sample_id"):
                out.append(sample)
            else:
                out.append(
                    {
                        "sample_id": aid,
                        "raw_topic": row.title or "",
                        "retrieval_tags": meta.get("retrieval_tags") or {},
                        "key_fragments": {"golden_hook": (row.content or "")[:120]},
                        "style_fingerprint": {},
                    }
                )
            if len(out) >= max(1, top_k):
                break
        return out

    def build_style_constraint_layer(self, retrieved: Sequence[Dict[str, Any]]) -> str:
        sentence_level = self.global_constraints.get("sentence_level") or {}
        vocab_level = self.global_constraints.get("vocabulary_level") or {}
        emotion_level = self.global_constraints.get("emotion_level") or {}
        data_level = self.global_constraints.get("data_level") or {}

        transition_words = ((self.global_constraints.get("paragraph_level") or {}).get("transition_words_required") or [])[:6]
        banned_words = (vocab_level.get("banned_words") or [])[:12]
        catchphrases = (vocab_level.get("mandatory_catchphrases") or [])[:8]
        markers = (emotion_level.get("emotional_markers") or [])[:6]

        snippets: List[str] = []
        for idx, sample in enumerate(retrieved[:3], start=1):
            fp = sample.get("style_fingerprint") or {}
            kf = sample.get("key_fragments") or {}
            hook = str(kf.get("golden_hook") or "")[:120]
            rhythm = str(fp.get("sentence_rhythm") or "")
            tag = str(sample.get("raw_topic") or sample.get("sample_id") or "")
            snippets.append(f"- 样本{idx}（{tag}）：节奏={rhythm}；hook={hook}")

        return (
            "## Style Constraint Layer（硬约束）\n"
            f"- 平均句长约 {sentence_level.get('avg_length', 18)} 字，短句占比约 {sentence_level.get('short_sentence_ratio', 0.6)}\n"
            f"- 反问句占比目标约 {sentence_level.get('rhetorical_question_ratio', 0.15)}\n"
            f"- 情绪曲线默认：{emotion_level.get('default_curve', '谷底→反弹→高光')}\n"
            f"- 必须出现转折/过渡词中的至少2个：{', '.join(transition_words) if transition_words else '（无）'}\n"
            f"- 推荐口头表达（至少2个）：{', '.join(catchphrases) if catchphrases else '（无）'}\n"
            f"- 禁用词（不得出现）：{', '.join(banned_words) if banned_words else '（无）'}\n"
            f"- 建议情绪标记：{', '.join(markers) if markers else '（无）'}\n"
            f"- 数据密度要求：{data_level.get('data_density', '每100字至少1个具体数字')}\n"
            "## 检索到的风格样本（只模仿结构与语感，禁止照抄事实）\n"
            + ("\n".join(snippets) if snippets else "- （无）")
        )

    def score_human_likeness(self, text: str) -> Dict[str, Any]:
        if not text:
            return {"burstiness_score": 0.0, "imperfection_score": 0.0, "pass": False, "issues": ["空内容"]}

        sentence_chunks = [s.strip() for s in re.split(r"[。！？!?；;\n]+", text) if s.strip()]
        lengths = [len(s) for s in sentence_chunks if s]
        if lengths:
            mean_len = sum(lengths) / len(lengths)
            variance = sum((x - mean_len) ** 2 for x in lengths) / max(1, len(lengths))
            burstiness = (math.sqrt(variance) / mean_len) if mean_len > 0 else 0.0
        else:
            burstiness = 0.0

        sentence_level = self.global_constraints.get("sentence_level") or {}
        imp_cfg = sentence_level.get("imperfection_injection") or {}
        filler_words = imp_cfg.get("filler_words") or ["呢", "啊", "吧"]
        filler_count = sum(text.count(str(w)) for w in filler_words if str(w))
        approx_word_count = max(1, len(re.findall(r"[\u4e00-\u9fa5A-Za-z0-9]", text)))
        imperfection = filler_count / approx_word_count

        vocab_level = self.global_constraints.get("vocabulary_level") or {}
        banned_words = [str(x) for x in (vocab_level.get("banned_words") or []) if str(x)]
        banned_hit = [w for w in banned_words if w in text]

        min_burstiness = _safe_float(self.quality_thresholds.get("min_burstiness"), 0.35)
        min_imperfection = _safe_float(imp_cfg.get("filler_density"), 0.03)
        passed = burstiness >= min_burstiness and imperfection >= min_imperfection and not banned_hit
        issues: List[str] = []
        if burstiness < min_burstiness:
            issues.append(f"burstiness_score 过低: {burstiness:.3f} < {min_burstiness:.3f}")
        if imperfection < min_imperfection:
            issues.append(f"imperfection_score 过低: {imperfection:.3f} < {min_imperfection:.3f}")
        if banned_hit:
            issues.append(f"出现禁用词: {', '.join(banned_hit[:4])}")
        return {
            "burstiness_score": round(burstiness, 4),
            "imperfection_score": round(imperfection, 4),
            "banned_words_hit": banned_hit[:8],
            "pass": passed,
            "issues": issues,
        }
