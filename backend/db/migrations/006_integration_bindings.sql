-- 第三方同步目标映射（如 飞书 space_id ↔ IP）
CREATE TABLE IF NOT EXISTS integration_bindings (
  id            VARCHAR(64) PRIMARY KEY,
  integration   VARCHAR(64) NOT NULL,
  ip_id         VARCHAR(64) NOT NULL,
  external_id   VARCHAR(255) NOT NULL,
  external_name VARCHAR(255),
  extra         JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_integration_bindings_ip FOREIGN KEY (ip_id) REFERENCES ip(ip_id)
);

CREATE INDEX IF NOT EXISTS idx_integration_bindings_integration ON integration_bindings(integration);
CREATE INDEX IF NOT EXISTS idx_integration_bindings_ip_id ON integration_bindings(ip_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_integration_ip ON integration_bindings(integration, ip_id);
