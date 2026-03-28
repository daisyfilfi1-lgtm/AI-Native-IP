-- 素材录入任务表（Phase 1）

CREATE TABLE IF NOT EXISTS ingest_tasks (
  task_id           VARCHAR(64) PRIMARY KEY,
  ip_id             VARCHAR(64) NOT NULL,
  source_type       VARCHAR(32) NOT NULL,
  source_url        VARCHAR(2048),
  local_file_id     VARCHAR(255),
  title             VARCHAR(255),
  notes             TEXT,
  status            VARCHAR(32) NOT NULL DEFAULT 'QUEUED',
  error_message     TEXT,
  created_asset_ids  JSONB NOT NULL DEFAULT '[]',
  created_at        TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_ingest_tasks_ip FOREIGN KEY (ip_id) REFERENCES ip(ip_id)
);

CREATE INDEX IF NOT EXISTS idx_ingest_tasks_ip_id ON ingest_tasks(ip_id);
CREATE INDEX IF NOT EXISTS idx_ingest_tasks_status ON ingest_tasks(status);
CREATE INDEX IF NOT EXISTS idx_ingest_tasks_created_at ON ingest_tasks(created_at);
