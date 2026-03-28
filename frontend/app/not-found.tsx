'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { Home, ArrowLeft } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="text-center max-w-md">
        {/* 404 Graphic */}
        <div className="relative mb-8">
          <div className="text-9xl font-bold text-gradient opacity-20">404</div>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-cyan flex items-center justify-center shadow-glow-lg">
              <span className="text-4xl">🤖</span>
            </div>
          </div>
        </div>

        {/* Message */}
        <h1 className="text-2xl font-bold text-foreground mb-3">
          页面未找到
        </h1>
        <p className="text-foreground-secondary mb-8">
          抱歉，您访问的页面不存在或已被移除。
          <br />
          请返回首页或检查链接是否正确。
        </p>

        {/* Actions */}
        <div className="flex items-center justify-center gap-3">
          <Button
            variant="secondary"
            leftIcon={<ArrowLeft className="w-4 h-4" />}
            onClick={() => window.history.back()}
          >
            返回上一页
          </Button>
          <Link href="/">
            <Button leftIcon={<Home className="w-4 h-4" />}>
              返回首页
            </Button>
          </Link>
        </div>

        {/* Help text */}
        <p className="mt-8 text-sm text-foreground-muted">
          如果问题持续存在，请联系技术支持
        </p>
      </div>
    </div>
  );
}
