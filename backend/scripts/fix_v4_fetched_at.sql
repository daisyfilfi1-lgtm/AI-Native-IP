-- 修复 V4 竞品视频的 fetched_at 字段
-- 问题：查询条件要求 fetched_at > NOW() - INTERVAL '7 days'，但旧数据的 fetched_at 可能已过期

-- 查看当前视频的时间分布
SELECT 
    CASE 
        WHEN fetched_at > NOW() - INTERVAL '7 days' THEN '最近7天'
        WHEN fetched_at > NOW() - INTERVAL '30 days' THEN '7-30天'
        ELSE '超过30天'
    END as time_range,
    COUNT(*) as video_count
FROM competitor_videos
GROUP BY 1;

-- 更新所有视频的 fetched_at 为当前时间（让数据可被查找到）
UPDATE competitor_videos 
SET fetched_at = NOW()
WHERE fetched_at < NOW() - INTERVAL '7 days';

-- 验证更新
SELECT COUNT(*) as total_videos FROM competitor_videos;
SELECT COUNT(*) as recent_videos FROM competitor_videos WHERE fetched_at > NOW() - INTERVAL '7 days';
