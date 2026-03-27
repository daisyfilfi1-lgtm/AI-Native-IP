'use client';

import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { 
  FileText, 
  Clock, 
  TrendingUp, 
  DollarSign,
  Sparkles,
  Plus,
  PenTool,
  ArrowRight,
  Zap,
  Target,
  Users
} from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  return (
    <MainLayout title="仪表盘">
      {/* Welcome banner */}
      <div className="mb-8 p-6 rounded-2xl bg-gradient-to-r from-primary-500/10 via-accent-cyan/10 to-accent-pink/10 border border-primary-500/20">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-foreground mb-2">
              欢迎回来，<span className="text-gradient">IP操盘手</span>
            </h2>
            <p className="text-foreground-secondary">
              AI-Native IP 工厂已就绪，开始您的内容生产之旅
            </p>
          </div>
          <Link href="/ip">
            <Button leftIcon={<Plus className="w-4 h-4" />}>
              新建IP
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-foreground-secondary">今日产出</p>
              <p className="mt-2 text-3xl font-bold text-foreground">3</p>
              <p className="text-xs text-foreground-tertiary mt-1">条内容</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-primary-500/10 flex items-center justify-center text-primary-400">
              <FileText className="w-5 h-5" />
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-foreground-secondary">人工审核</p>
              <p className="mt-2 text-3xl font-bold text-foreground">5分钟</p>
              <p className="text-xs text-foreground-tertiary mt-1">今日累计</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-accent-cyan/10 flex items-center justify-center text-accent-cyan">
              <Clock className="w-5 h-5" />
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-foreground-secondary">过审率</p>
              <p className="mt-2 text-3xl font-bold text-accent-green">92%</p>
              <p className="text-xs text-accent-green mt-1">↑ 5% 较上周</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-accent-green/10 flex items-center justify-center text-accent-green">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-foreground-secondary">单条成本</p>
              <p className="mt-2 text-3xl font-bold text-foreground">¥12.5</p>
              <p className="text-xs text-accent-green mt-1">↓ 30% 较传统方式</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-accent-yellow/10 flex items-center justify-center text-accent-yellow">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
        </Card>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Creator Workbench */}
        <Link href="/creator/dashboard">
          <Card className="h-full hover:border-primary-500/50 transition-all group cursor-pointer">
            <div className="p-5">
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-accent-cyan flex items-center justify-center">
                  <PenTool className="w-6 h-6 text-white" />
                </div>
                <Badge variant="primary" size="sm">推荐</Badge>
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2 group-hover:text-primary-400 transition-colors">
                IP创作者工作台
              </h3>
              <p className="text-sm text-foreground-secondary mb-4">
                智能选题、仿写爆款、爆款原创（Original），AI Agent助你高效产出
              </p>
              <div className="flex items-center text-primary-400 text-sm font-medium">
                开始创作 <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          </Card>
        </Link>

        {/* IP Management */}
        <Link href="/ip">
          <Card className="h-full hover:border-primary-500/50 transition-all group cursor-pointer">
            <div className="p-5">
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent-pink to-purple-600 flex items-center justify-center">
                  <Users className="w-6 h-6 text-white" />
                </div>
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2 group-hover:text-primary-400 transition-colors">
                IP资产管理
              </h3>
              <p className="text-sm text-foreground-secondary mb-4">
                管理你的IP矩阵，追踪资产价值和变现数据
              </p>
              <div className="flex items-center text-primary-400 text-sm font-medium">
                查看IP <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          </Card>
        </Link>

        {/* Agent Config */}
        <Link href="/agents">
          <Card className="h-full hover:border-primary-500/50 transition-all group cursor-pointer">
            <div className="p-5">
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
                  <Zap className="w-6 h-6 text-white" />
                </div>
                <Badge variant="success" size="sm">已就绪</Badge>
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2 group-hover:text-primary-400 transition-colors">
                7-Agent配置
              </h3>
              <p className="text-sm text-foreground-secondary mb-4">
                配置7大AI Agent，定制你的专属内容工作流
              </p>
              <div className="flex items-center text-primary-400 text-sm font-medium">
                配置Agent <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          </Card>
        </Link>
      </div>

      {/* System Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader 
            title="快速开始" 
            description="常用功能入口"
          />
          <div className="grid grid-cols-2 gap-3">
            <Link href="/creator/dashboard">
              <div className="p-4 rounded-xl bg-background-tertiary hover:bg-background-elevated transition-colors cursor-pointer">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-500 to-accent-cyan flex items-center justify-center mb-3">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <p className="text-sm font-medium text-foreground">开始创作</p>
                <p className="text-xs text-foreground-tertiary mt-1">使用AI生成内容</p>
              </div>
            </Link>
            <Link href="/creator/library">
              <div className="p-4 rounded-xl bg-background-tertiary hover:bg-background-elevated transition-colors cursor-pointer">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-accent-green to-emerald-600 flex items-center justify-center mb-3">
                  <FileText className="w-5 h-5 text-white" />
                </div>
                <p className="text-sm font-medium text-foreground">内容库</p>
                <p className="text-xs text-foreground-tertiary mt-1">管理已生成内容</p>
              </div>
            </Link>
          </div>
        </Card>

        <Card>
          <CardHeader 
            title="系统状态" 
            description="各组件运行情况"
          />
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-accent-green" />
                <span className="text-sm text-foreground">API服务</span>
              </div>
              <Badge variant="success" size="sm">正常</Badge>
            </div>
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-accent-green" />
                <span className="text-sm text-foreground">前端构建</span>
              </div>
              <Badge variant="success" size="sm">正常</Badge>
            </div>
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-accent-green" />
                <span className="text-sm text-foreground">Agent工作流</span>
              </div>
              <Badge variant="success" size="sm">运行中</Badge>
            </div>
          </div>
        </Card>
      </div>
    </MainLayout>
  );
}
