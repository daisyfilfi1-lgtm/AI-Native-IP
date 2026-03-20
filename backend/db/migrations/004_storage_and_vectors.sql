-- 对象存储文件元数据
CREATE TABLE IF NOT EXISTS file_objects (
  file_id        VARCHAR(64) PRIMARY KEY,
  ip_id          VARCHAR(64) NOT NULL,
  provider       VARCHAR(32) NOT NULL DEFAULT 's3',
  bucket         VARCHAR(255) NOT NULL,
  object_key     VARCHAR(1024) NOT NULL,
  file_name      VARCHAR(255),
  content_type   VARCHAR(128),
  size_bytes     BIGINT NOT NULL DEFAULT 0,
  etag           VARCHAR(128),
  created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_file_objects_ip FOREIGN KEY (ip_id) REFERENCES ip(ip_id)
);

CREATE INDEX IF NOT EXISTS idx_file_objects_ip_id ON file_objects(ip_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_file_objects_bucket_key ON file_objects(bucket, object_key);

-- 向量存储（Phase 1: JSONB 存储 embedding，便于快速落地；后续可平滑迁移 pgvector / 外部向量库）
CREATE TABLE IF NOT EXISTS asset_vectors (
  asset_id       VARCHAR(64) PRIMARY KEY,
  ip_id          VARCHAR(64) NOT NULL,
  embedding      JSONB NOT NULL,
  dim            INT NOT NULL,
  model          VARCHAR(128) NOT NULL,
  created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_asset_vectors_asset FOREIGN KEY (asset_id) REFERENCES ip_assets(asset_id) ON DELETE CASCADE,
  CONSTRAINT fk_asset_vectors_ip FOREIGN KEY (ip_id) REFERENCES ip(ip_id)
);

CREATE INDEX IF NOT EXISTS idx_asset_vectors_ip_id ON asset_vectors(ip_id);
