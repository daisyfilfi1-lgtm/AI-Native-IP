-- IP 风格画像（从素材提取后持久化，供生成与风格接口使用）
ALTER TABLE ip ADD COLUMN IF NOT EXISTS style_profile JSONB;
