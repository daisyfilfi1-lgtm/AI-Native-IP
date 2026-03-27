'use client';

import { cn } from '@/lib/utils';
import { ChevronDown } from 'lucide-react';
import { forwardRef, SelectHTMLAttributes } from 'react';

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helper?: string;
  options: { value: string; label: string }[];
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, helper, options, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-foreground mb-2">
            {label}
          </label>
        )}
        <div className="relative">
          <select
            ref={ref}
            className={cn(
              'w-full appearance-none',
              'bg-background-tertiary',
              'border border-border',
              'rounded-xl',
              'text-foreground',
              'transition-all duration-200',
              'focus:outline-none focus:border-primary-500/50 focus:ring-2 focus:ring-primary-500/20',
              'hover:border-border-hover',
              error && 'border-accent-red focus:border-accent-red focus:ring-accent-red/20',
              'px-4 py-3 pr-10',
              className
            )}
            {...props}
          >
            {options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-tertiary pointer-events-none" />
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

Select.displayName = 'Select';

export { Select };
