'use client';

import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/Card';
import { ArrowUpRight, ArrowDownRight, LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  description?: string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  icon: LucideIcon;
  iconColor?: string;
  className?: string;
}

export function StatCard({
  title,
  value,
  description,
  trend,
  icon: Icon,
  iconColor = 'text-primary-400',
  className,
}: StatCardProps) {
  return (
    <Card hover className={cn('', className)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-foreground-secondary">{title}</p>
          <p className="mt-2 text-3xl font-bold text-foreground">{value}</p>
          
          {(description || trend) && (
            <div className="mt-2 flex items-center gap-2">
              {trend && (
                <span
                  className={cn(
                    'inline-flex items-center gap-0.5 text-xs font-medium',
                    trend.isPositive ? 'text-accent-green' : 'text-accent-red'
                  )}
                >
                  {trend.isPositive ? (
                    <ArrowUpRight className="w-3 h-3" />
                  ) : (
                    <ArrowDownRight className="w-3 h-3" />
                  )}
                  {Math.abs(trend.value)}%
                </span>
              )}
              {description && (
                <span className="text-xs text-foreground-tertiary">{description}</span>
              )}
            </div>
          )}
        </div>
        
        <div
          className={cn(
            'w-10 h-10 rounded-xl',
            'bg-background-tertiary',
            'flex items-center justify-center',
            iconColor
          )}
        >
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </Card>
  );
}
