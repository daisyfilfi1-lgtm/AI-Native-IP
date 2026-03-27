'use client';

import { cn } from '@/lib/utils';
import { forwardRef } from 'react';

interface ProgressProps {
  value: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'gradient' | 'success' | 'warning' | 'danger';
  showValue?: boolean;
  className?: string;
}

const Progress = forwardRef<HTMLDivElement, ProgressProps>(
  ({ value, max = 100, size = 'md', variant = 'default', showValue, className }, ref) => {
    const percentage = Math.min(100, Math.max(0, (value / max) * 100));

    const sizes = {
      sm: 'h-1',
      md: 'h-2',
      lg: 'h-3',
    };

    const variants = {
      default: 'bg-primary-500',
      gradient: 'bg-gradient-to-r from-primary-500 via-accent-cyan to-accent-pink',
      success: 'bg-accent-green',
      warning: 'bg-accent-yellow',
      danger: 'bg-accent-red',
    };

    return (
      <div ref={ref} className={cn('w-full', className)}>
        <div className="flex items-center gap-3">
          <div className={cn('flex-1 bg-background-tertiary rounded-full overflow-hidden', sizes[size])}>
            <div
              className={cn('h-full rounded-full transition-all duration-500 ease-out', variants[variant])}
              style={{ width: `${percentage}%` }}
            />
          </div>
          {showValue && (
            <span className="text-sm font-medium text-foreground-secondary min-w-[3rem] text-right">
              {Math.round(percentage)}%
            </span>
          )}
        </div>
      </div>
    );
  }
);

Progress.displayName = 'Progress';

export { Progress };
