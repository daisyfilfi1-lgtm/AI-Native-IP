-- Migration: 015_competitor_four_dim.sql
-- Description: 添加四维评分字段到竞品视频表
-- Created: 2026-03-28

-- 添加四维评分字段
ALTER TABLE competitor_videos 
ADD COLUMN IF NOT EXISTS four_dim_relevance FLOAT DEFAULT 0.5,
ADD COLUMN IF NOT EXISTS four_dim_hotness FLOAT DEFAULT 0.5,
ADD COLUMN IF NOT EXISTS four_dim_competition FLOAT DEFAULT 0.5,
ADD COLUMN IF NOT EXISTS four_dim_conversion FLOAT DEFAULT 0.5,
ADD COLUMN IF NOT EXISTS four_dim_total FLOAT DEFAULT 0.5;

-- 添加 URL、原始响应（TIKHub 等）
ALTER TABLE competitor_videos 
ADD COLUMN IF NOT EXISTS url VARCHAR(500);

ALTER TABLE competitor_videos
ADD COLUMN IF NOT EXISTS raw_data JSONB DEFAULT '{}';

-- 创建索引优化四维排序查询
CREATE INDEX IF NOT EXISTS idx_competitor_videos_four_dim_total ON competitor_videos(four_dim_total DESC);
CREATE INDEX IF NOT EXISTS idx_competitor_videos_composite ON competitor_videos(competitor_id, four_dim_total DESC);

-- 注释说明
COMMENT ON COLUMN competitor_videos.four_dim_relevance IS '四维评分-相关度 (0-1)';
COMMENT ON COLUMN competitor_videos.four_dim_hotness IS '四维评分-热度 (0-1)';
COMMENT ON COLUMN competitor_videos.four_dim_competition IS '四维评分-竞争度 (0-1, 越低越好)';
COMMENT ON COLUMN competitor_videos.four_dim_conversion IS '四维评分-转化率 (0-1)';
COMMENT ON COLUMN competitor_videos.four_dim_total IS '四维总分 (加权计算)';
COMMENT ON COLUMN competitor_videos.raw_data IS '抓取原始 JSON（调试用）';

-- 更新现有数据的四维分数（基于已有数据计算）
UPDATE competitor_videos SET
    four_dim_relevance = CASE 
        WHEN content_type = 'money' THEN 0.8
        WHEN content_type = 'emotion' THEN 0.7
        WHEN content_type = 'skill' THEN 0.6
        ELSE 0.5 
    END,
    four_dim_hotness = LEAST(1.0, like_count::float / 100000),
    four_dim_competition = CASE 
        WHEN content_type = 'money' THEN 0.8
        WHEN content_type = 'emotion' THEN 0.6
        WHEN content_type = 'skill' THEN 0.5
        ELSE 0.3 
    END,
    four_dim_conversion = CASE 
        WHEN content_type = 'money' THEN 0.8
        WHEN content_type = 'skill' THEN 0.7
        WHEN content_type = 'emotion' THEN 0.5
        ELSE 0.3 
    END;

-- 更新总分
UPDATE competitor_videos SET
    four_dim_total = (
        four_dim_relevance * 0.3 +
        four_dim_hotness * 0.3 +
        (1 - four_dim_competition) * 0.2 +
        four_dim_conversion * 0.2
    );
