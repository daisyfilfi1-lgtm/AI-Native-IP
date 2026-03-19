-- 集成配置表：存储飞书等第三方凭证（管理后台填写后写入）
CREATE TABLE IF NOT EXISTS integration_config (
  key          VARCHAR(64) PRIMARY KEY,
  value_json   JSONB NOT NULL DEFAULT '{}',
  updated_at   TIMESTAMP NOT NULL DEFAULT NOW()
);
