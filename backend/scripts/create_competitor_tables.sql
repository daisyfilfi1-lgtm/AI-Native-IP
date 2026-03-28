-- 竞品视频表
-- 用于存储竞品账号的热门视频，作为选题推荐的数据源

CREATE TABLE IF NOT EXISTS competitor_videos (
    id SERIAL PRIMARY KEY,
    video_id VARCHAR(64) NOT NULL,
    competitor_id VARCHAR(64) NOT NULL,
    title TEXT,
    desc TEXT,
    author VARCHAR(255),
    platform VARCHAR(32) DEFAULT 'douyin',
    
    -- 数据表现
    play_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    
    -- 内容分析
    tags JSONB DEFAULT '[]',
    content_type VARCHAR(32),  -- money/emotion/skill/life
    content_structure JSONB DEFAULT '{}',  -- 存储内容结构分析结果
    
    -- 时间
    create_time TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    UNIQUE(video_id, competitor_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_competitor_videos_competitor ON competitor_videos(competitor_id);
CREATE INDEX IF NOT EXISTS idx_competitor_videos_fetched_at ON competitor_videos(fetched_at);
CREATE INDEX IF NOT EXISTS idx_competitor_videos_play_count ON competitor_videos(play_count);
CREATE INDEX IF NOT EXISTS idx_competitor_videos_content_type ON competitor_videos(content_type);

-- 触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_competitor_videos_updated_at ON competitor_videos;
CREATE TRIGGER update_competitor_videos_updated_at
    BEFORE UPDATE ON competitor_videos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 插入示例数据（小敏IP的竞品）
-- 实际使用时，这些数据会通过API抓取自动填充

INSERT INTO competitor_videos (
    video_id, competitor_id, title, desc, author, platform,
    play_count, like_count, content_type, content_structure, create_time
) VALUES 
-- 逆袭/转变类
('vid_001', 'comp_001', '30岁被裁员后，我用这个方法月入5万', 
 '被裁员后没有放弃，尝试了3个副业，终于找到适合自己的方法', 
 '某职场博主', 'douyin', 158000, 23000, 'money',
 '{"hook_type": "数字", "conflict": "被裁员", "emotion": "励志", "target_audience": "职场人"}',
 '2024-01-15 10:00:00'),

-- 坦白/揭秘类
('vid_002', 'comp_001', '揭秘副业行业内幕：这5个坑千万别踩', 
 '做了3年副业，踩过无数坑，今天分享给你们避坑指南', 
 '某职场博主', 'douyin', 89000, 12000, 'money',
 '{"hook_type": "揭秘", "conflict": "踩坑", "emotion": "警示", "target_audience": "想搞副业的人"}',
 '2024-01-14 15:30:00'),

-- 教程/方法类
('vid_003', 'comp_002', '宝妈在家赚钱的3个方法，亲测有效', 
 '带娃的同时也能有收入，分享我的3个方法', 
 '某宝妈博主', 'douyin', 234000, 45000, 'money',
 '{"hook_type": "数字", "conflict": "带娃没收入", "emotion": "实用", "target_audience": "宝妈"}',
 '2024-01-13 09:00:00'),

-- 故事/经历类
('vid_004', 'comp_002', '从手心向上到月入3万：一个宝妈的3年创业史', 
 '记录我从全职妈妈到创业宝妈的转变历程', 
 '某宝妈博主', 'douyin', 312000, 67000, 'emotion',
 '{"hook_type": "对比", "conflict": "手心向上", "emotion": "共鸣", "target_audience": "宝妈"}',
 '2024-01-12 20:00:00'),

-- 对比类
('vid_005', 'comp_003', '副业前后的我：这3个变化太明显了', 
 '做副业前后的生活状态对比', 
 '某成长博主', 'douyin', 145000, 28000, 'emotion',
 '{"hook_type": "对比", "conflict": "", "emotion": "励志", "target_audience": "职场人"}',
 '2024-01-11 14:00:00')

ON CONFLICT (video_id, competitor_id) DO UPDATE SET
    play_count = EXCLUDED.play_count,
    like_count = EXCLUDED.like_count,
    updated_at = CURRENT_TIMESTAMP;

-- 查看示例数据
SELECT 
    video_id,
    title,
    author,
    play_count,
    like_count,
    content_type,
    fetched_at
FROM competitor_videos
ORDER BY play_count DESC
LIMIT 10;
