'use client';

import { MainLayout } from '@/components/layout/MainLayout';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { Agent } from '@/types';
import { 
  Brain, 
  GitBranch, 
  FileText, 
  Shield, 
  Video, 
  BarChart3,
  Sparkles,
  Settings,
  Play,
  Pause,
  ArrowRight,
  MessageSquare
} from 'lucide-react';
import Link from 'next/link';

const agents: Agent[] = [
  {
    id: 'memory',
    name: '记忆Agent',
    nameEn: 'Memory Agent',
    description: '构建IP实时数字孪生，管理素材库和语义检索。将IP过往所有内容转化为可检索的数字资产，支持模糊查询和智能标签化。',
    icon: '🧠',
    color: 'from-violet-500 to-purple-600',
    status: 'active',
  },
  {
    id: 'strategy',
    name: '策略Agent',
    nameEn: 'Strategy Agent',
    description: '决策内容选题和投放策略。24小时抓取全网低粉爆款，四维评分模型智能决策，预测性选题预测未来7天热点。',
    icon: '🎯',
    color: 'from-cyan-500 to-blue-600',
    status: 'active',
  },
  {
    id: 'remix',
    name: '重组Agent',
    nameEn: 'Remix Agent',
    description: '竞品解构并IP化重组。分析爆款视频结构，合法借鉴并替换为IP独家素材，确保原创度>75%。',
    icon: '🔀',
    color: 'from-pink-500 to-rose-600',
    status: 'active',
  },
  {
    id: 'generation',
    name: '生成Agent',
    nameEn: 'Generation Agent',
    description: '转化为符合IP风格的终稿文案。基于50条S级文案Fine-tune专属模型，植入口头禅和语言指纹，去AI化处理。',
    icon: '✍️',
    color: 'from-amber-500 to-orange-600',
    status: 'configuring',
  },
  {
    id: 'compliance',
    name: '合规Agent',
    nameEn: 'Compliance Agent',
    description: '工业刹车系统。三级审查机制（平台/广告法/原创），分平台规则适配，自动修正违规内容。',
    icon: '🛡️',
    color: 'from-emerald-500 to-teal-600',
    status: 'active',
  },
  {
    id: 'visual',
    name: '视觉Agent',
    nameEn: 'Visual Agent',
    description: '文案转视觉方案。B级内容数字人自动拍摄，A级内容智能分镜脚本，情绪-景别自动映射。',
    icon: '🎬',
    color: 'from-blue-500 to-indigo-600',
    status: 'active',
  },
  {
    id: 'analytics',
    name: '分析Agent',
    nameEn: 'Analytics Agent',
    description: '自动化数据归因与策略迭代。实时监测播放量/完播率/互动率，自动周报生成，反馈闭环优化。',
    icon: '📊',
    color: 'from-purple-500 to-cyan-600',
    status: 'inactive',
  },
];

const statusConfig = {
  active: { label: '运行中', variant: 'success' as const, actionIcon: Pause, actionLabel: '停止' },
  inactive: { label: '已停止', variant: 'default' as const, actionIcon: Play, actionLabel: '启动' },
  configuring: { label: '配置中', variant: 'warning' as const, actionIcon: Settings, actionLabel: '配置' },
};

export default function AgentsPage() {
  const activeCount = agents.filter(a => a.status === 'active').length;

  return (
    <MainLayout title="7-Agent工作流">
      {/* Quick Config Banner */}
      <Link href="/agents/onboarding">
        <Card className="mb-6 hover:border-primary-500/50 transition-all group cursor-pointer">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent-pink to-purple-600 flex items-center justify-center">
              <MessageSquare className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-foreground group-hover:text-primary-400 transition-colors">
                  🎉 全新：对话式配置引导
                </h2>
                <Badge variant="primary" size="sm">推荐</Badge>
              </div>
              <p className="text-sm text-foreground-secondary mt-1">
                不需要理解复杂的技术参数，只需回答几个简单问题，AI助手帮你完成所有配置
              </p>
            </div>
            <div className="hidden sm:flex items-center gap-2 text-primary-400">
              <span className="text-sm font-medium">开始配置</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </Card>
      </Link>

      {/* Overview banner */}
      <div className="mb-8 p-6 rounded-2xl bg-gradient-to-r from-primary-500/10 via-accent-cyan/10 to-accent-pink/10 border border-primary-500/20">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-accent-cyan flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-foreground">7-Agent 智能协作系统</h2>
            <p className="text-foreground-secondary">工业化内容生产，日产300条，IP每日仅需45分钟终审</p>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-accent-green" />
            <span className="text-sm text-foreground-secondary">{activeCount}/7 运行中</span>
          </div>
          <div className="h-4 w-px bg-border" />
          <div className="flex items-center gap-2">
            <span className="text-sm text-foreground-secondary">工作流自动串联</span>
          </div>
          <div className="h-4 w-px bg-border" />
          <div className="flex items-center gap-2">
            <span className="text-sm text-foreground-secondary">数据闭环反馈</span>
          </div>
        </div>
      </div>

      {/* Agents Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {agents.map((agent, index) => {
          const status = statusConfig[agent.status];
          const StatusIcon = status.actionIcon;
          const isLast = index === agents.length - 1;

          return (
            <Card key={agent.id} hover className="relative">
              {/* Connection line to next agent */}
              {!isLast && (
                <div className="hidden lg:block absolute -bottom-6 left-8 w-px h-6 bg-border z-0" />
              )}
              
              <div className="flex items-start gap-4">
                {/* Icon */}
                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${agent.color} flex items-center justify-center flex-shrink-0 shadow-lg`}>
                  <span className="text-2xl">{agent.icon}</span>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-semibold text-foreground">{agent.name}</h3>
                        <Badge variant={status.variant} size="sm" dot>{status.label}</Badge>
                      </div>
                      <p className="text-xs text-foreground-tertiary">{agent.nameEn}</p>
                    </div>
                    <span className="text-2xs text-foreground-muted font-mono">#{String(index + 1).padStart(2, '0')}</span>
                  </div>

                  <p className="text-sm text-foreground-secondary mb-4 line-clamp-2">
                    {agent.description}
                  </p>

                  {/* Config progress */}
                  <div className="mb-4">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs text-foreground-tertiary">配置完整度</span>
                      <span className="text-xs font-medium text-foreground">{agent.status === 'active' ? '100%' : '75%'}</span>
                    </div>
                    <Progress 
                      value={agent.status === 'active' ? 100 : 75} 
                      size="sm" 
                      variant={agent.status === 'active' ? 'success' : 'warning'} 
                    />
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
                      {status.actionLabel}
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Workflow diagram hint */}
      <Card className="mt-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex -space-x-2">
              {agents.slice(0, 4).map((agent) => (
                <div 
                  key={agent.id} 
                  className={`w-8 h-8 rounded-full bg-gradient-to-br ${agent.color} flex items-center justify-center text-xs border-2 border-background`}
                >
                  {agent.icon}
                </div>
              ))}
              <div className="w-8 h-8 rounded-full bg-background-elevated flex items-center justify-center text-xs border-2 border-background">
                +3
              </div>
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">工作流可视化</p>
              <p className="text-xs text-foreground-secondary">查看Agent之间的数据流和协作关系</p>
            </div>
          </div>
          <Button variant="ghost" rightIcon={<ArrowRight className="w-4 h-4" />}>
            查看
          </Button>
        </div>
      </Card>
    </MainLayout>
  );
}
