'use client';

import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Progress } from '@/components/ui/Progress';
import { Agent } from '@/types';
import { Settings, Play, Pause, AlertCircle } from 'lucide-react';
import Link from 'next/link';

interface AgentCardProps {
  agent: Agent;
  className?: string;
}

const statusConfig = {
  active: { label: '运行中', variant: 'success' as const, icon: Play },
  inactive: { label: '已停止', variant: 'default' as const, icon: Pause },
  configuring: { label: '配置中', variant: 'warning' as const, icon: AlertCircle },
};

export function AgentCard({ agent, className }: AgentCardProps) {
  const status = statusConfig[agent.status];
  const StatusIcon = status.icon;

  return (
    <Card hover className={cn('group', className)}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'w-10 h-10 rounded-xl flex items-center justify-center',
              'bg-gradient-to-br',
              agent.color
            )}
          >
            <span className="text-lg">{agent.icon}</span>
          </div>
          <div>
            <h3 className="font-semibold text-foreground">{agent.name}</h3>
            <p className="text-xs text-foreground-tertiary">{agent.nameEn}</p>
          </div>
        </div>
        <Badge variant={status.variant} dot>
          {status.label}
        </Badge>
      </div>

      <p className="text-sm text-foreground-secondary mb-4 line-clamp-2">
        {agent.description}
      </p>

      {/* Config completeness */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-foreground-tertiary">配置完整度</span>
          <span className="text-xs font-medium text-foreground">75%</span>
        </div>
        <Progress value={75} size="sm" variant="gradient" />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Link href={`/agents/${agent.id}`} className="flex-1">
          <Button variant="secondary" size="sm" className="w-full" leftIcon={<Settings className="w-3.5 h-3.5" />}>
            配置
          </Button>
        </Link>
        <Button
          variant={agent.status === 'active' ? 'danger' : 'primary'}
          size="sm"
          leftIcon={<StatusIcon className="w-3.5 h-3.5" />}
        >
          {agent.status === 'active' ? '停止' : '启动'}
        </Button>
      </div>
    </Card>
  );
}
