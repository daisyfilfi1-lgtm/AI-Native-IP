'use client';

import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';
import { ButtonHTMLAttributes, forwardRef } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ 
    className, 
    variant = 'primary', 
    size = 'md', 
    isLoading, 
    leftIcon, 
    rightIcon,
    children,
    disabled,
    ...props 
  }, ref) => {
    const variants = {
      primary: cn(
        'bg-gradient-to-r from-primary-600 to-accent-cyan',
        'text-white',
        'hover:from-primary-500 hover:to-accent-cyan/90',
        'shadow-glow hover:shadow-glow-lg',
        'border-0'
      ),
      secondary: cn(
        'bg-background-elevated',
        'text-foreground',
        'hover:bg-background-tertiary',
        'border border-border hover:border-border-hover'
      ),
      ghost: cn(
        'bg-transparent',
        'text-foreground-secondary',
        'hover:text-foreground hover:bg-background-tertiary',
        'border border-transparent'
      ),
      danger: cn(
        'bg-accent-red/10',
        'text-accent-red',
        'hover:bg-accent-red/20',
        'border border-accent-red/30'
      ),
      outline: cn(
        'bg-transparent',
        'text-foreground',
        'hover:bg-background-tertiary',
        'border border-border hover:border-border-hover'
      ),
    };

    const sizes = {
      sm: 'h-8 px-3 text-xs',
      md: 'h-10 px-4 text-sm',
      lg: 'h-12 px-6 text-base',
    };

    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-2',
          'rounded-xl font-medium',
          'transition-all duration-200',
          'focus:outline-none focus:ring-2 focus:ring-primary-500/50',
          'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none',
          variants[variant],
          sizes[size],
          className
        )}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
        {!isLoading && leftIcon}
        {children}
        {!isLoading && rightIcon}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button };
