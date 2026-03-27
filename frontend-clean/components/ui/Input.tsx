'use client';

import { cn } from '@/lib/utils';
import { forwardRef, InputHTMLAttributes, ReactNode } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helper?: string;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, helper, leftIcon, rightIcon, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-foreground mb-2">
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground-tertiary">
              {leftIcon}
            </div>
          )}
          <input
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
              error && 'border-accent-red focus:border-accent-red focus:ring-accent-red/20',
              leftIcon && 'pl-10',
              rightIcon && 'pr-10',
              'px-4 py-3',
              className
            )}
            {...props}
          />
          {rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground-tertiary">
              {rightIcon}
            </div>
          )}
        </div>
        {error && (
          <p className="mt-1.5 text-sm text-accent-red">{error}</p>
        )}
        {helper && !error && (
          <p className="mt-1.5 text-sm text-foreground-tertiary">{helper}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

interface TextareaProps extends InputHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helper?: string;
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, helper, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-foreground mb-2">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          className={cn(
            'w-full min-h-[120px]',
            'bg-background-tertiary',
            'border border-border',
            'rounded-xl',
            'text-foreground placeholder:text-foreground-muted',
            'transition-all duration-200',
            'focus:outline-none focus:border-primary-500/50 focus:ring-2 focus:ring-primary-500/20',
            'hover:border-border-hover',
            error && 'border-accent-red focus:border-accent-red focus:ring-accent-red/20',
            'px-4 py-3 resize-y',
            className
          )}
          {...props}
        />
        {error && (
          <p className="mt-1.5 text-sm text-accent-red">{error}</p>
        )}
        {helper && !error && (
          <p className="mt-1.5 text-sm text-foreground-tertiary">{helper}</p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

export { Input, Textarea };
