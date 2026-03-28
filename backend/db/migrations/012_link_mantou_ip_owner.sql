-- 将 IP「馒头女子」归属到手机号 18600200850 对应用户
-- 前提：该手机号已至少通过验证码登录一次（users 表中存在该 phone）
-- 若名称不完全一致，可改为: AND i.name LIKE '%馒头女子%'

UPDATE ip AS i
SET
  owner_user_id = u.user_id,
  updated_at = NOW()
FROM users AS u
WHERE u.phone = '18600200850'
  AND i.name = '馒头女子';
