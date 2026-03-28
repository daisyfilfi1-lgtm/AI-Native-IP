'use client';

import { cn } from '@/lib/utils';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { WorkflowStatus } from '@/types';
import { 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  Clock,
  ArrowRight
} from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';

interface WorkflowTimelineProps {
  workflows: WorkflowStatus[];
  className?: string;
}

const statusConfig = {
  running: { label: '运行中', variant: 'info' as const, icon: Loader2 },
  completed: { label: '已完成', variant: 'success' as const, icon: CheckCircle2 },
  failed: { label: '失败', variant: 'danger' as const, icon: XCircle },
  pending: { label: '待执行', variant: 'default' as const, icon: Clock },
};

export function WorkflowTimeline({ workflows, className }: WorkflowTimelineProps) {
  return (
    <Card className={cn('', className)}>
      <CardHeader 
        title="工作流状态" 
        description="实时查看7-Agent工作流执行情况"
      />
      
      <div className="space-y-4">
        {workflows.map((workflow, index) => {
          const status = statusConfig[workflow.status];
          const StatusIcon = status.icon;
          const isLast = index === workflows.length - 1;

          return (
            <div key={workflow.id} className="relative">
              {!isLast && (
                <div className="absolute left-5 top-10 bottom-0 w-px bg-border" />
              )}
              
              <div className="flex gap-4">
                {/* Status icon */}
                <div
                  className={cn(
                    'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0',
                    workflow.status === 'running' && 'bg-accent-cyan/10',
                    workflow.status === 'completed' && 'bg-accent-green/10',
                    workflow.status === 'failed' && 'bg-accent-red/10',
                    workflow.status === 'pending' && 'bg-background-elevated'
                  )}
                >
                  <StatusIcon
                    className={cn(
                      'w-5 h-5',
                      workflow.status === 'running' && 'text-accent-cyan animate-spin',
                      workflow.status === 'completed' && 'text-accent-green',
                      workflow.status === 'failed' && 'text-accent-red',
                      workflow.status === 'pending' && 'text-foreground-tertiary'
                    )}
                  />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h4 className="text-sm font-medium text-foreground">
                        {workflow.name}
                      </h4>
                      <p className="text-xs text-foreground-tertiary mt-0.5">
                        {workflow.agent && `执行Agent: ${workflow.agent}`}
                      </p>
                    </div>
                    <Badge variant={status.variant} size="sm">
                      {status.label}
                    </Badge>
                  </div>

                  {/* Progress bar for running tasks */}
                  {workflow.status === 'running' && (
                    <div className="mt-3">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs text-foreground-tertiary">进度</span>
                        <span className="text-xs font-medium text-foreground">
                          {workflow.progress}%
                        </span>
                      </div>
                      <div className="h-1.5 bg-background-tertiary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-primary-500 to-accent-cyan rounded-full transition-all duration-500"
                          style={{ width: `${workflow.progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Time */}
                  {workflow.startTime && (
                    <p className="mt-2 text-xs text-foreground-muted">
                      {formatRelativeTime(workflow.startTime)}
                    </p>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {workflows.length === 0 && (
          <div className="text-center py-8">
            <div className="w-12 h-12 rounded-full bg-background-tertiary flex items-center justify-center mx-auto mb-3">
              <Clock className="w-5 h-5 text-foreground-tertiary" />
            </div>
            <p className="text-sm text-foreground-secondary">暂无运行中的工作流</p>
          </div>
        )}
      </div>
    </Card>
  );
}
