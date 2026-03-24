-- 状态机：心跳字段，用于卡死判定（集成执行标准 v1.0）
ALTER TABLE ingest_tasks ADD COLUMN IF NOT EXISTS last_heartbeat TIMESTAMP;
CREATE INDEX IF NOT EXISTS idx_ingest_tasks_last_heartbeat ON ingest_tasks(last_heartbeat) WHERE status = 'PROCESSING';
