'use client';

import { cn } from '@/lib/utils';
import { forwardRef, HTMLAttributes } from 'react';

type BadgeVariant = 'default' | 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info' | 'outline';
type BadgeSize = 'sm' | 'md';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: BadgeSize;
  dot?: boolean;
}

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', size = 'sm', dot, children, ...props }, ref) => {
    const variants: Record<BadgeVariant, string> = {
      default: 'bg-background-elevated text-foreground-secondary border-border',
      primary: 'bg-primary-500/10 text-primary-400 border-primary-500/20',
      secondary: 'bg-background-tertiary text-foreground border-border',
      success: 'bg-accent-green/10 text-accent-green border-accent-green/20',
      warning: 'bg-accent-yellow/10 text-accent-yellow border-accent-yellow/20',
      danger: 'bg-accent-red/10 text-accent-red border-accent-red/20',
      info: 'bg-accent-cyan/10 text-accent-cyan border-accent-cyan/20',
      outline: 'bg-transparent text-foreground border-border',
    };

    const sizes: Record<BadgeSize, string> = {
      sm: 'text-2xs px-2 py-0.5',
      md: 'text-xs px-2.5 py-1',
    };

    const dotColors: Record<BadgeVariant, string> = {
      default: 'bg-foreground-secondary',
      primary: 'bg-primary-400',
      secondary: 'bg-foreground-tertiary',
      success: 'bg-accent-green',
      warning: 'bg-accent-yellow',
      danger: 'bg-accent-red',
      info: 'bg-accent-cyan',
      outline: 'bg-foreground',
    };

    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center gap-1.5',
          'rounded-full border',
          'font-medium',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {dot && (
          <span className={cn('w-1.5 h-1.5 rounded-full', dotColors[variant])} />
        )}
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

export { Badge };
