'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { loginWithSms } from '@/lib/auth';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

export default function LoginPage() {
  const router = useRouter();
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await loginWithSms(phone.trim(), code.trim());
      router.push('/');
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <Card className="w-full max-w-md p-8">
        <h1 className="text-xl font-semibold text-foreground mb-1">登录</h1>
        <p className="text-sm text-foreground-secondary mb-6">
          使用手机号与短信验证码登录。短信通道未开通时，请使用联调验证码（默认{' '}
          <code className="text-primary-400">123456</code>），对应后端字段为 <code className="text-primary-400">code</code>
          ，不是密码体系。
        </p>
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="login-phone" className="block text-sm text-foreground-secondary mb-1.5">
              手机号
            </label>
            <Input
              id="login-phone"
              name="phone"
              type="tel"
              inputMode="numeric"
              autoComplete="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="11 位手机号"
              required
              aria-describedby={error ? 'login-error' : undefined}
            />
          </div>
          <div>
            <label htmlFor="login-code" className="block text-sm text-foreground-secondary mb-1.5">
              验证码
            </label>
            <Input
              id="login-code"
              name="code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="测试环境填 123456"
              required
              aria-describedby={error ? 'login-error' : undefined}
            />
          </div>
          {error ? (
            <p id="login-error" className="text-sm text-accent-red" role="alert">
              {error}
            </p>
          ) : null}
          <Button type="submit" id="login-submit" name="login" className="w-full" disabled={loading}>
            {loading ? '登录中…' : '登录'}
          </Button>
        </form>
        <p className="mt-6 text-xs text-foreground-tertiary text-center">
          <Link href="/" className="text-primary-400 hover:underline">
            返回首页
          </Link>
        </p>
      </Card>
    </div>
  );
}
