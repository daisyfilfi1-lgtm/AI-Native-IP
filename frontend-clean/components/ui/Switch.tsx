'use client';

import { cn } from '@/lib/utils';
import { forwardRef, InputHTMLAttributes } from 'react';

interface SwitchProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
  description?: string;
}

const Switch = forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, label, description, ...props }, ref) => {
    return (
      <label className={cn('flex items-start gap-3 cursor-pointer', className)}>
        <div className="relative flex-shrink-0 mt-0.5">
          <input
            ref={ref}
            type="checkbox"
            className="sr-only peer"
            {...props}
          />
          <div
            className={cn(
              'w-11 h-6 rounded-full transition-colors duration-200',
              'bg-background-elevated peer-checked:bg-primary-500',
              'border border-border peer-checked:border-primary-500'
            )}
          />
          <div
            className={cn(
              'absolute left-1 top-1',
              'w-4 h-4 rounded-full bg-foreground',
              'transition-transform duration-200',
              'peer-checked:translate-x-5'
            )}
          />
        </div>
        {(label || description) && (
          <div className="flex-1">
            {label && (
              <span className="block text-sm font-medium text-foreground">
                {label}
              </span>
            )}
            {description && (
              <span className="block text-sm text-foreground-tertiary mt-0.5">
                {description}
              </span>
            )}
          </div>
        )}
      </label>
    );
  }
);

Switch.displayName = 'Switch';

export { Switch };
