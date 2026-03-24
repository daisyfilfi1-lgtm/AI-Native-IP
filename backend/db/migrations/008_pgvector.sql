-- pgvector 扩展与向量列迁移（替代 JSONB 存储）
-- 注：迁移脚本按分号拆分，故不使用 DO $$ 块
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE asset_vectors ADD COLUMN IF NOT EXISTS embedding_vec vector(1536);

UPDATE asset_vectors
SET embedding_vec = (embedding::text)::vector(1536)
WHERE dim = 1536 AND embedding_vec IS NULL AND embedding IS NOT NULL;

ALTER TABLE asset_vectors DROP COLUMN IF EXISTS embedding;

ALTER TABLE asset_vectors RENAME COLUMN embedding_vec TO embedding;
