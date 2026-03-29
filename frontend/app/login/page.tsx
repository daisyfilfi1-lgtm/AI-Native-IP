'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { loginWithEmailPassword, loginWithSms } from '@/lib/auth';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

type LoginMode = 'email' | 'sms';

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<LoginMode>('email');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function onSubmitEmail(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await loginWithEmailPassword(email.trim(), password);
      router.push('/');
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setLoading(false);
    }
  }

  async function onSubmitSms(e: React.FormEvent) {
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
        <div className="flex gap-1 p-1 mb-6 rounded-lg bg-background-tertiary">
          <button
            type="button"
            onClick={() => {
              setMode('email');
              setError('');
            }}
            className={cn(
              'flex-1 py-2 text-sm font-medium rounded-md transition-colors',
              mode === 'email'
                ? 'bg-background-elevated text-foreground shadow-sm'
                : 'text-foreground-secondary hover:text-foreground'
            )}
          >
            邮箱密码
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('sms');
              setError('');
            }}
            className={cn(
              'flex-1 py-2 text-sm font-medium rounded-md transition-colors',
              mode === 'sms'
                ? 'bg-background-elevated text-foreground shadow-sm'
                : 'text-foreground-secondary hover:text-foreground'
            )}
          >
            手机验证码
          </button>
        </div>

        {mode === 'email' ? (
          <form onSubmit={onSubmitEmail} className="space-y-4" noValidate>
            <p className="text-sm text-foreground-secondary">
              使用注册时的邮箱与密码（后端 <code className="text-primary-400">POST /api/auth/login</code>）。
            </p>
            <div>
              <label htmlFor="login-email" className="block text-sm text-foreground-secondary mb-1.5">
                邮箱
              </label>
              <Input
                id="login-email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="例如 18600200850@local"
                required
                aria-describedby={error ? 'login-error' : undefined}
              />
            </div>
            <div>
              <label htmlFor="login-password" className="block text-sm text-foreground-secondary mb-1.5">
                密码
              </label>
              <Input
                id="login-password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="密码"
                required
                aria-describedby={error ? 'login-error' : undefined}
              />
            </div>
            {error ? (
              <p id="login-error" className="text-sm text-accent-red" role="alert">
                {error}
              </p>
            ) : null}
            <Button type="submit" id="login-submit-email" className="w-full" disabled={loading}>
              {loading ? '登录中…' : '登录'}
            </Button>
          </form>
        ) : (
          <form onSubmit={onSubmitSms} className="space-y-4" noValidate>
            <p className="text-sm text-foreground-secondary">
              使用手机号与短信验证码。短信未开通时，联调验证码默认{' '}
              <code className="text-primary-400">123456</code>（字段为 <code className="text-primary-400">code</code>）。
            </p>
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
            <Button type="submit" id="login-submit-sms" name="login" className="w-full" disabled={loading}>
              {loading ? '登录中…' : '登录'}
            </Button>
          </form>
        )}
        <p className="mt-6 text-xs text-foreground-tertiary text-center">
          <Link href="/" className="text-primary-400 hover:underline">
            返回首页
          </Link>
        </p>
      </Card>
    </div>
  );
}
