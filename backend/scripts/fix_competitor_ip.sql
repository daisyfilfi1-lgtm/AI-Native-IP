-- Fix: 将竞品账号从 xiaomin 迁移到 xiaomin1 (馒头女子)
-- 原因：用户登录的是 xiaomin1，但竞品配置到了 xiaomin

-- 首先确保 xiaomin1 IP 存在
INSERT INTO ip (ip_id, name, owner_user_id, status, created_at, updated_at)
VALUES ('xiaomin1', '馒头女子', 'system', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (ip_id) DO NOTHING;

-- 更新竞品账号的 ip_id 从 xiaomin 到 xiaomin1
UPDATE competitor_accounts 
SET ip_id = 'xiaomin1' 
WHERE ip_id = 'xiaomin';

-- 验证迁移结果
SELECT '竞品账号迁移完成' as result;
SELECT ip_id, COUNT(*) as competitor_count 
FROM competitor_accounts 
GROUP BY ip_id;
