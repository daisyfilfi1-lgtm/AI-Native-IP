-- Phase 1 初始化表结构（与 phase1-architecture.md 对齐）

CREATE TABLE IF NOT EXISTS ip (
  ip_id         VARCHAR(64) PRIMARY KEY,
  name          VARCHAR(255) NOT NULL,
  owner_user_id VARCHAR(64) NOT NULL,
  status        VARCHAR(32) NOT NULL DEFAULT 'active',
  created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ip_assets (
  asset_id          VARCHAR(64) PRIMARY KEY,
  ip_id             VARCHAR(64) NOT NULL,
  asset_type        VARCHAR(32) NOT NULL,
  title             VARCHAR(255),
  content           TEXT NOT NULL,
  content_vector_ref VARCHAR(128),
  metadata          JSONB NOT NULL DEFAULT '{}',
  relations         JSONB NOT NULL DEFAULT '[]',
  status            VARCHAR(32) NOT NULL DEFAULT 'active',
  created_at        TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_ip_assets_ip FOREIGN KEY (ip_id) REFERENCES ip(ip_id)
);

CREATE INDEX IF NOT EXISTS idx_ip_assets_ip_id ON ip_assets(ip_id);
CREATE INDEX IF NOT EXISTS idx_ip_assets_status ON ip_assets(status);
CREATE INDEX IF NOT EXISTS idx_ip_assets_metadata_gin ON ip_assets USING GIN (metadata);

CREATE TABLE IF NOT EXISTS tag_config (
  config_id     VARCHAR(64) PRIMARY KEY,
  ip_id         VARCHAR(64) NOT NULL UNIQUE,
  tag_categories JSONB NOT NULL,
  version       INT NOT NULL DEFAULT 1,
  updated_by    VARCHAR(64) NOT NULL,
  updated_at    TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_tag_config_ip FOREIGN KEY (ip_id) REFERENCES ip(ip_id)
);

CREATE TABLE IF NOT EXISTS memory_config (
  config_id    VARCHAR(64) PRIMARY KEY,
  ip_id        VARCHAR(64) NOT NULL UNIQUE,
  retrieval    JSONB NOT NULL,
  usage_limits JSONB NOT NULL,
  version      INT NOT NULL DEFAULT 1,
  updated_by   VARCHAR(64) NOT NULL,
  updated_at   TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_memory_config_ip FOREIGN KEY (ip_id) REFERENCES ip(ip_id)
);

CREATE TABLE IF NOT EXISTS config_history (
  id          VARCHAR(64) PRIMARY KEY,
  ip_id       VARCHAR(64) NOT NULL,
  agent_type  VARCHAR(64) NOT NULL,
  version     INT NOT NULL,
  config_json JSONB NOT NULL,
  changed_by  VARCHAR(64) NOT NULL,
  changed_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_config_history_ip_agent ON config_history(ip_id, agent_type);

CREATE TABLE IF NOT EXISTS content_drafts (
  draft_id          VARCHAR(64) PRIMARY KEY,
  ip_id             VARCHAR(64) NOT NULL,
  level             VARCHAR(8) NOT NULL,
  workflow          JSONB NOT NULL,
  quality_score     JSONB NOT NULL,
  compliance_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  created_at        TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_content_drafts_ip FOREIGN KEY (ip_id) REFERENCES ip(ip_id)
);

CREATE INDEX IF NOT EXISTS idx_content_drafts_ip_id ON content_drafts(ip_id);

