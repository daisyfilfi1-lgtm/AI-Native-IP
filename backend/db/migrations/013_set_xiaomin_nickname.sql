-- 为实测 IP 固化昵称，保证文案自称稳定
UPDATE ip
SET nickname = '小敏',
    updated_at = NOW()
WHERE ip_id = 'xiaomin1'
  AND (nickname IS NULL OR nickname = '');

