'use client';

import { cn } from '@/lib/utils';
import { forwardRef, TextareaHTMLAttributes } from 'react';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: string;
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          'w-full',
          'bg-background-tertiary',
          'border border-border',
          'rounded-xl',
          'text-foreground placeholder:text-foreground-muted',
          'transition-all duration-200',
          'focus:outline-none focus:border-primary-500/50 focus:ring-2 focus:ring-primary-500/20',
          'hover:border-border-hover',
          'px-4 py-3',
          error && 'border-accent-red focus:border-accent-red focus:ring-accent-red/20',
          className
        )}
        {...props}
      />
    );
  }
);

Textarea.displayName = 'Textarea';

export { Textarea };
