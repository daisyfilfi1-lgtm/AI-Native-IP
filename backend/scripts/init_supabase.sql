-- AI-Native IP 数据库初始化脚本
-- 在 Supabase SQL 编辑器中执行

-- 1. IP 表
CREATE TABLE IF NOT EXISTS "ip" (
    ip_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    owner_user_id VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    nickname VARCHAR(100),
    bio VARCHAR(500),
    monetization_model VARCHAR(50),
    target_audience VARCHAR(255),
    content_direction VARCHAR(255),
    unique_value_prop VARCHAR(500),
    expertise VARCHAR(255),
    passion VARCHAR(255),
    market_demand VARCHAR(255),
    product_service VARCHAR(255),
    price_range VARCHAR(100),
    repurchase_rate VARCHAR(50)
);

-- 2. IP 素材表
CREATE TABLE IF NOT EXISTS "ip_assets" (
    asset_id VARCHAR(64) PRIMARY KEY,
    ip_id VARCHAR(64) NOT NULL REFERENCES "ip"(ip_id),
    asset_type VARCHAR(32) NOT NULL,
    title VARCHAR(255),
    content TEXT NOT NULL,
    content_vector_ref VARCHAR(128),
    metadata JSONB NOT NULL DEFAULT '{}',
    relations JSONB NOT NULL DEFAULT '[]',
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ip_assets_ip_id ON "ip_assets"(ip_id);
CREATE INDEX IF NOT EXISTS idx_ip_assets_metadata_gin ON "ip_assets" USING GIN(metadata);

-- 3. 标签配置表
CREATE TABLE IF NOT EXISTS "tag_config" (
    config_id VARCHAR(64) PRIMARY KEY,
    ip_id VARCHAR(64) NOT NULL REFERENCES "ip"(ip_id),
    tag_categories JSONB NOT NULL DEFAULT '{}',
    version INTEGER NOT NULL DEFAULT 1,
    updated_by VARCHAR(64) NOT NULL
);

-- 4. 记忆配置表
CREATE TABLE IF NOT EXISTS "memory_config" (
    config_id VARCHAR(64) PRIMARY KEY,
    ip_id VARCHAR(64) NOT NULL REFERENCES "ip"(ip_id),
    config_json JSONB NOT NULL DEFAULT '{}',
    version INTEGER NOT NULL DEFAULT 1,
    updated_by VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 5. 配置历史表
CREATE TABLE IF NOT EXISTS "config_history" (
    history_id VARCHAR(64) PRIMARY KEY,
    ip_id VARCHAR(64) NOT NULL REFERENCES "ip"(ip_id),
    config_json JSONB NOT NULL DEFAULT '{}',
    version INTEGER NOT NULL,
    change_type VARCHAR(32) NOT NULL,
    changed_by VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 6. 录入任务表
CREATE TABLE IF NOT EXISTS "ingest_task" (
    task_id VARCHAR(64) PRIMARY KEY,
    ip_id VARCHAR(64) NOT NULL REFERENCES "ip"(ip_id),
    source_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 7. 内容草稿表
CREATE TABLE IF NOT EXISTS "content_draft" (
    draft_id VARCHAR(64) PRIMARY KEY,
    ip_id VARCHAR(64) NOT NULL REFERENCES "ip"(ip_id),
    content TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 8. 文件对象表
CREATE TABLE IF NOT EXISTS "file_object" (
    file_id VARCHAR(64) PRIMARY KEY,
    ip_id VARCHAR(64) NOT NULL REFERENCES "ip"(ip_id),
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(32) NOT NULL,
    file_size BIGINT,
    storage_path VARCHAR(512),
    file_meta JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 9. 向量数据表
CREATE TABLE IF NOT EXISTS "asset_vector" (
    vector_id VARCHAR(64) PRIMARY KEY,
    asset_id VARCHAR(64) NOT NULL REFERENCES "ip_assets"(asset_id),
    ip_id VARCHAR(64) NOT NULL REFERENCES "ip"(ip_id),
    vector_data JSONB NOT NULL,
    model VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_asset_vector_ip_id ON "asset_vector"(ip_id);

-- 10. 集成配置表
CREATE TABLE IF NOT EXISTS "integration_config" (
    config_id VARCHAR(64) PRIMARY KEY,
    key VARCHAR(128) NOT NULL UNIQUE,
    value_text TEXT,
    value_json JSONB,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 11. 集成绑定表
CREATE TABLE IF NOT EXISTS "integration_binding" (
    binding_id VARCHAR(64) PRIMARY KEY,
    integration VARCHAR(64) NOT NULL,
    ip_id VARCHAR(64) NOT NULL REFERENCES "ip"(ip_id),
    external_id VARCHAR(255),
    external_name VARCHAR(255),
    extra JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(integration, ip_id)
);

SELECT '数据库初始化完成！' AS result;
