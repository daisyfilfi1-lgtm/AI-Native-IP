-- 策略 Agent：评分卡/权重/抓取配置（JSON 存 ip.strategy_config）+ 竞品账号表

ALTER TABLE ip ADD COLUMN IF NOT EXISTS strategy_config JSONB;

CREATE TABLE IF NOT EXISTS competitor_accounts (
  competitor_id   VARCHAR(64) PRIMARY KEY,
  ip_id           VARCHAR(64) NOT NULL,
  name            VARCHAR(255) NOT NULL,
  platform        VARCHAR(64) NOT NULL DEFAULT '',
  followers_display VARCHAR(64),
  notes           TEXT,
  created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_competitor_accounts_ip FOREIGN KEY (ip_id) REFERENCES ip(ip_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_competitor_accounts_ip_id ON competitor_accounts(ip_id);
