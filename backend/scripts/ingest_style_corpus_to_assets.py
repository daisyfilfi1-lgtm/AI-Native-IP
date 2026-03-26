"""
将 docs/IP知识库 的 style corpus 导入 ip_assets + asset_vectors（pgvector）。

用法：
  py -3 scripts/ingest_style_corpus_to_assets.py --ip-id xiaomin1
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

# 项目路径初始化
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from app.env_loader import load_backend_env
from app.db.session import SessionLocal
from app.db.models import IPAsset
from app.services.vector_service import upsert_asset_vector

load_backend_env()


def _corpus_path() -> Path:
    return (
        Path(backend_dir).parent
        / "docs"
        / "IP知识库"
        / "小敏IP_Style_Corpus_完整26条_预训练素材库.json"
    )


def _asset_id(sample_id: str) -> str:
    s = (sample_id or "").strip().lower().replace("-", "_")
    return f"sc_{s}"[:64]


def _build_index_text(sample: Dict[str, Any]) -> str:
    tags = sample.get("retrieval_tags") or {}
    entities = sample.get("content_entities") or {}
    fp = sample.get("style_fingerprint") or {}
    kf = sample.get("key_fragments") or {}
    parts: List[str] = [
        f"sample_id: {sample.get('sample_id', '')}",
        f"content_type: {sample.get('content_type', '')}",
        f"raw_topic: {sample.get('raw_topic', '')}",
    ]
    for key in ("theme_vector", "emotion_tags", "target_audience", "scene_context"):
        val = tags.get(key)
        if isinstance(val, list) and val:
            parts.append(f"{key}: {'；'.join(str(x) for x in val)}")
    for key in ("core_topic", "pain_point", "solution", "key_concept"):
        v = entities.get(key)
        if v:
            parts.append(f"{key}: {v}")
    if fp.get("sentence_rhythm"):
        parts.append(f"sentence_rhythm: {fp.get('sentence_rhythm')}")
    if kf.get("golden_hook"):
        parts.append(f"golden_hook: {kf.get('golden_hook')}")
    return "\n".join(parts)


def ingest(db: Session, *, ip_id: str, dry_run: bool = False) -> Dict[str, int]:
    path = _corpus_path()
    if not path.exists():
        raise FileNotFoundError(f"corpus file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        corpus = json.load(f)
    samples = corpus.get("samples") or []
    created, updated, vectored = 0, 0, 0
    for sample in samples:
        sample_id = str(sample.get("sample_id") or "").strip()
        if not sample_id:
            continue
        aid = _asset_id(sample_id)
        title = f"[StyleCorpus] {sample_id} {str(sample.get('raw_topic') or '')}".strip()
        content = _build_index_text(sample)
        meta = {
            "source": "style_corpus",
            "sample_id": sample_id,
            "content_type": sample.get("content_type"),
            "retrieval_tags": sample.get("retrieval_tags") or {},
            "style_corpus_sample": sample,
        }
        row = db.query(IPAsset).filter(IPAsset.asset_id == aid).first()
        if row:
            row.ip_id = ip_id
            row.asset_type = "text"
            row.title = title[:255]
            row.content = content
            row.asset_meta = meta
            row.status = "active"
            updated += 1
        else:
            row = IPAsset(
                asset_id=aid,
                ip_id=ip_id,
                asset_type="text",
                title=title[:255],
                content=content,
                asset_meta=meta,
                relations=[],
                status="active",
            )
            db.add(row)
            created += 1
        if not dry_run:
            ok = upsert_asset_vector(
                db,
                asset_id=aid,
                ip_id=ip_id,
                content=content,
                force=True,
            )
            if ok:
                vectored += 1
    if not dry_run:
        db.commit()
    else:
        db.rollback()
    return {"created": created, "updated": updated, "vectored": vectored, "total_samples": len(samples)}


def main() -> None:
    parser = argparse.ArgumentParser(description="导入style corpus到ip_assets并回填pgvector")
    parser.add_argument("--ip-id", required=True, help="目标IP ID，如 xiaomin1")
    parser.add_argument("--dry-run", action="store_true", help="仅预演，不落库")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        stat = ingest(db, ip_id=args.ip_id, dry_run=args.dry_run)
        print(json.dumps(stat, ensure_ascii=False))
    finally:
        db.close()


if __name__ == "__main__":
    main()
