-- pgvector 扩展与向量列迁移（替代 JSONB 存储）
CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'asset_vectors' AND column_name = 'embedding'
    AND udt_name = 'jsonb'
  ) THEN
    ALTER TABLE asset_vectors ADD COLUMN IF NOT EXISTS embedding_vec vector(1536);
    UPDATE asset_vectors
    SET embedding_vec = (embedding::text)::vector(1536)
    WHERE dim = 1536 AND embedding IS NOT NULL;
    ALTER TABLE asset_vectors DROP COLUMN embedding;
    ALTER TABLE asset_vectors RENAME COLUMN embedding_vec TO embedding;
  END IF;
END
$$;
