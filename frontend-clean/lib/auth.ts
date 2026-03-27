/** 手机号 + 验证码登录（JWT），与 backend /api/auth/sms/login 一致 */

const TOKEN_KEY = 'ip_factory_auth_token';

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export interface LoginResult {
  token: string;
  user: { userId: string; phone: string };
}

/**
 * 测试环境（短信未开通）：后端在 SMS_PROVIDER=mock 或未关 OTP_BYPASS 时，
 * 验证码填环境变量 OTP_BYPASS_CODE，默认 123456（不是「密码」字段，请求体字段名仍为 code）。
 */
export async function loginWithSms(phone: string, code: string): Promise<LoginResult> {
  const res = await fetch('/api/auth/sms/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone, code }),
  });
  const raw = (await res.json().catch(() => ({}))) as LoginResult & { detail?: unknown };
  if (!res.ok) {
    const d = raw.detail;
    let msg: string;
    if (typeof d === 'string') msg = d;
    else if (Array.isArray(d))
      msg = d.map((x: { msg?: string }) => x.msg || '').filter(Boolean).join(', ') || `登录失败 (${res.status})`;
    else msg = `登录失败 (${res.status})`;
    throw new Error(msg);
  }
  const data = raw;
  if (!data.token) {
    throw new Error('响应缺少 token');
  }
  setStoredToken(data.token);
  return data;
}
