'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui/Button';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('App Error:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 rounded-full bg-accent-red/10 flex items-center justify-center mx-auto mb-4">
          <span className="text-2xl">⚠️</span>
        </div>
        <h2 className="text-xl font-bold text-foreground mb-2">
          页面加载出错
        </h2>
        <p className="text-foreground-secondary mb-4">
          {error.message || '抱歉，页面加载时发生错误'}
        </p>
        <div className="flex gap-3 justify-center">
          <Button onClick={() => reset()}>
            重试
          </Button>
          <Button variant="secondary" onClick={() => window.location.href = '/'}>
            返回首页
          </Button>
        </div>
        {error.digest && (
          <p className="mt-4 text-xs text-foreground-muted font-mono">
            Error ID: {error.digest}
          </p>
        )}
      </div>
    </div>
  );
}
