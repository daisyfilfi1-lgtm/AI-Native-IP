'use client';

import { cn } from '@/lib/utils';
import { Bell, Search, User } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface HeaderProps {
  className?: string;
  title?: string;
}

export function Header({ className, title }: HeaderProps) {
  return (
    <header
      className={cn(
        'h-16',
        'bg-background/80 backdrop-blur-xl',
        'border-b border-border',
        'flex items-center justify-between px-6',
        'sticky top-0 z-30',
        className
      )}
    >
      {/* Left side */}
      <div className="flex items-center gap-4">
        {title && (
          <h1 className="text-xl font-semibold text-foreground">{title}</h1>
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Search */}
        <div className="relative hidden sm:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-tertiary" />
          <input
            id="header-search"
            name="q"
            type="search"
            placeholder="搜索..."
            autoComplete="off"
            className={cn(
              'w-64 h-9 pl-9 pr-4',
              'bg-background-tertiary',
              'border border-border rounded-lg',
              'text-sm text-foreground placeholder:text-foreground-muted',
              'focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20',
              'transition-all duration-200'
            )}
          />
        </div>

        {/* Notifications */}
        <Button variant="ghost" size="sm" className="relative">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-accent-red" />
        </Button>

        {/* User */}
        <Button variant="ghost" size="sm" className="gap-2">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary-500 to-accent-cyan flex items-center justify-center">
            <User className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="hidden sm:inline text-sm">管理员</span>
        </Button>
      </div>
    </header>
  );
}
