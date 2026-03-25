-- 手机号 + 验证码登录：用户表与 OTP 记录

CREATE TABLE IF NOT EXISTS users (
  user_id      VARCHAR(64) PRIMARY KEY,
  phone        VARCHAR(20) NOT NULL UNIQUE,
  created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMP NOT NULL DEFAULT NOW(),
  last_login_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);

CREATE TABLE IF NOT EXISTS auth_otp (
  id           BIGSERIAL PRIMARY KEY,
  phone        VARCHAR(20) NOT NULL,
  code_hash    VARCHAR(128) NOT NULL,
  expires_at   TIMESTAMP NOT NULL,
  consumed     BOOLEAN NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_otp_phone_created ON auth_otp(phone, created_at DESC);
