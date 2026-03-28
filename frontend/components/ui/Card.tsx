'use client';

import { cn } from '@/lib/utils';
import { forwardRef, HTMLAttributes } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'gradient';
  hover?: boolean;
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', hover = false, children, ...props }, ref) => {
    const variants = {
      default: cn(
        'bg-background-secondary',
        'border border-border',
        'rounded-2xl'
      ),
      glass: cn(
        'bg-background-secondary/50',
        'backdrop-blur-xl',
        'border border-white/10',
        'rounded-2xl'
      ),
      gradient: cn(
        'relative',
        'bg-background-secondary',
        'rounded-2xl',
        'before:absolute before:inset-0 before:rounded-2xl',
        'before:bg-gradient-to-br before:from-primary-500/20 before:to-accent-cyan/20',
        'before:-z-10',
        'after:absolute after:inset-[1px] after:rounded-2xl',
        'after:bg-background-secondary after:-z-10'
      ),
    };

    return (
      <div
        ref={ref}
        className={cn(
          variants[variant],
          'p-6',
          hover && 'transition-all duration-300 hover:border-border-hover hover:shadow-glow',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  description?: string;
  action?: React.ReactNode;
}

const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, title, description, action, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex items-start justify-between mb-4', className)}
      {...props}
    >
      <div className="flex-1 min-w-0">
        {title && (
          <h3 className="text-lg font-semibold text-foreground">{title}</h3>
        )}
        {description && (
          <p className="mt-1 text-sm text-foreground-secondary">{description}</p>
        )}
        {children}
      </div>
      {action && <div className="ml-4 flex-shrink-0">{action}</div>}
    </div>
  )
);

CardHeader.displayName = 'CardHeader';

interface CardContentProps extends HTMLAttributes<HTMLDivElement> {}

const CardContent = forwardRef<HTMLDivElement, CardContentProps>(
  ({ className, children, ...props }, ref) => (
    <div ref={ref} className={cn('', className)} {...props}>
      {children}
    </div>
  )
);

CardContent.displayName = 'CardContent';

export { Card, CardHeader, CardContent };
