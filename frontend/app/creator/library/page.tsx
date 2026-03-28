'use client';

import { useState, useEffect, useCallback } from 'react';
import { useCreatorIp } from '@/contexts/CreatorIpContext';
import { CreatorLayout } from '@/components/creator/CreatorLayout';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { creatorApi } from '@/lib/api/creator';
import type { LibraryItem } from '@/types/creator';
import type { LucideIcon } from 'lucide-react';
import { 
  FileText,
  Eye,
  Heart,
  MoreHorizontal,
  Play,
  Trash2,
  RefreshCw,
  Filter,
  BarChart3,
  Clock,
  ThumbsUp,
  MessageSquare,
  Users,
  X
} from 'lucide-react';
import Link from 'next/link';

interface TabConfig {
  value: string;
  label: string;
  count: number;
}

type BadgeVariant = 'default' | 'primary' | 'success' | 'warning';

interface StatusConfig {
  label: string;
  variant: BadgeVariant;
}

const tabs: TabConfig[] = [
  { value: 'all', label: '全部', count: 28 },
  { value: 'pending', label: '待审核', count: 3 },
  { value: 'published', label: '已发布', count: 22 },
  { value: 'viral', label: '爆款', count: 3 },
  { value: 'draft', label: '草稿', count: 3 },
];

const statusConfig: Record<LibraryItem['status'], StatusConfig> = {
  draft: { label: '草稿', variant: 'default' },
  pending: { label: '待审核', variant: 'warning' },
  published: { label: '已发布', variant: 'primary' },
  viral: { label: '爆款', variant: 'success' },
};

// 4维数据诊断配置
const METRICS_CONFIG = [
  {
    key: 'completion_rate',
    name: '完播率',
    icon: Clock,
    threshold: 30,
    unit: '%',
    suggestion: '需优化开头钩子',
    color: 'text-accent-cyan',
    bgColor: 'bg-accent-cyan/10',
    borderColor: 'border-accent-cyan/20'
  },
  {
    key: 'like_rate',
    name: '点赞率',
    icon: ThumbsUp,
    threshold: 3,
    unit: '%',
    suggestion: '需增强价值密度',
    color: 'text-accent-pink',
    bgColor: 'bg-accent-pink/10',
    borderColor: 'border-accent-pink/20'
  },
  {
    key: 'comment_rate',
    name: '评论率',
    icon: MessageSquare,
    threshold: 1,
    unit: '%',
    suggestion: '需增加争议性话题',
    color: 'text-accent-yellow',
    bgColor: 'bg-accent-yellow/10',
    borderColor: 'border-accent-yellow/20'
  },
  {
    key: 'follow_rate',
    name: '转粉率',
    icon: Users,
    threshold: 0.5,
    unit: '%',
    suggestion: '需强化人设记忆点',
    color: 'text-accent-green',
    bgColor: 'bg-accent-green/10',
    borderColor: 'border-accent-green/20'
  }
];

export default function CreatorLibraryPage() {
  const { ipId, loading: ipCtxLoading, needsLogin, noIp } = useCreatorIp();
  const [activeTab, setActiveTab] = useState('all');
  const [contents, setContents] = useState<LibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedContent, setSelectedContent] = useState<LibraryItem | null>(null);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadContents = useCallback(async () => {
    if (!ipId) return;
    setLoading(true);
    try {
      const status = activeTab === 'all' ? undefined : activeTab;
      const data: LibraryItem[] = await creatorApi.getLibraryItems(status, ipId);
      setContents(data);
    } catch (error) {
      console.error('Failed to load contents:', error);
    } finally {
      setLoading(false);
    }
  }, [activeTab, ipId]);

  useEffect(() => {
    if (ipCtxLoading) return;
    if (!ipId) {
      setContents([]);
      setLoading(false);
      return;
    }
    void loadContents();
  }, [ipCtxLoading, ipId, loadContents]);

  const formatNumber = (num: number): string => {
    if (num >= 10000) return (num / 10000).toFixed(1) + 'w';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
  };

  const getViews = (content: LibraryItem): number => content.metrics?.views ?? 0;
  const getLikes = (content: LibraryItem): number => content.metrics?.likes ?? 0;

  const handleDelete = async (content: LibraryItem, e: React.MouseEvent) => {
    e.stopPropagation(); // 防止触发卡片点击
    if (deletingId) return;
    const ok = window.confirm(`确认删除「${content.title}」吗？删除后不可恢复。`);
    if (!ok) return;
    setDeletingId(content.id);
    try {
      await creatorApi.deleteLibraryItem(content.id);
      // 从列表中移除已删除的项
      setContents(prev => prev.filter(item => item.id !== content.id));
    } catch (error) {
      console.error('Delete failed:', error);
      window.alert(error instanceof Error ? error.message : '删除失败，请稍后重试');
    } finally {
      setDeletingId(null);
    }
  };

  const handleCardClick = (content: LibraryItem) => {
    // 点击卡片查看内容详情
    if (content.status === 'published' || content.status === 'viral') {
      setSelectedContent(content);
      setShowAnalytics(true);
    } else if (content.status === 'draft') {
      // 草稿跳转到编辑页面
      window.alert('草稿编辑功能即将开放');
    } else if (content.status === 'pending') {
      // 待审核查看详情
      window.alert('审核详情功能即将开放');
    }
  };

  return (
    <CreatorLayout>
      {needsLogin && (
        <div className="mb-4 p-4 rounded-xl bg-background-tertiary border border-border text-sm text-foreground-secondary">
          请先 <Link href="/login" className="text-primary-400 font-medium hover:underline">登录</Link>
          后查看与你账号绑定的 IP 内容库。
        </div>
      )}
      {noIp && (
        <div className="mb-4 p-4 rounded-xl bg-background-tertiary border border-border text-sm text-foreground-secondary">
          暂无 IP。请前往{' '}
          <Link href="/ip" className="text-primary-400 font-medium hover:underline">IP 管理</Link> 创建。
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">我的内容库</h1>
          <p className="text-sm text-foreground-secondary">管理和复用你的所有内容</p>
        </div>
        <Button variant="secondary" leftIcon={<Filter className="w-4 h-4" />}>
          筛选
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-all',
              activeTab === tab.value
                ? 'bg-primary-500 text-white'
                : 'bg-background-tertiary text-foreground-secondary hover:text-foreground'
            )}
          >
            {tab.label}
            <span className={cn(
              'px-1.5 py-0.5 rounded text-xs',
              activeTab === tab.value ? 'bg-white/20' : 'bg-background-elevated'
            )}>
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* Content Grid */}
      {ipCtxLoading || loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {contents.map((content) => (
            <Card 
              key={content.id}
              className="group overflow-hidden hover:border-primary-500/50 transition-colors cursor-pointer"
              onClick={() => handleCardClick(content)}
            >
              {/* Thumbnail Placeholder */}
              <div className="aspect-video bg-gradient-to-br from-background-tertiary to-background-elevated flex items-center justify-center relative">
                <FileText className="w-12 h-12 text-foreground-tertiary" />
                
                {/* Status Badge */}
                <div className="absolute top-3 right-3">
                  <Badge variant={statusConfig[content.status].variant} size="sm">
                    {statusConfig[content.status].label}
                  </Badge>
                </div>

                {/* Hover Actions */}
                <div className="absolute inset-0 bg-black/50 flex items-center justify-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button className="w-10 h-10 rounded-full bg-white flex items-center justify-center hover:scale-110 transition-transform">
                    <Play className="w-5 h-5 text-foreground" />
                  </button>
                </div>
              </div>

              {/* Content Info */}
              <div className="p-4">
                <h3 className="font-semibold text-foreground mb-2 line-clamp-2 group-hover:text-primary-400 transition-colors">
                  {content.title}
                </h3>

                {/* Stats */}
                <div className="flex items-center gap-4 text-sm text-foreground-secondary mb-3">
                  {getViews(content) > 0 && (
                    <div className="flex items-center gap-1">
                      <Eye className="w-4 h-4" />
                      <span>{formatNumber(getViews(content))}</span>
                    </div>
                  )}
                  {getLikes(content) > 0 && (
                    <div className="flex items-center gap-1">
                      <Heart className="w-4 h-4" />
                      <span>{formatNumber(getLikes(content))}</span>
                    </div>
                  )}
                  <span className="text-xs text-foreground-tertiary">
                    {new Date(content.createdAt).toLocaleDateString('zh-CN')}
                  </span>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  {content.status === 'draft' && (
                    <Button size="sm" className="flex-1" onClick={(e) => { e.stopPropagation(); window.alert('草稿编辑入口即将开放'); }}>
                      继续编辑
                    </Button>
                  )}
                  {content.status === 'pending' && (
                    <Button
                      size="sm"
                      variant="secondary"
                      className="flex-1"
                      onClick={(e) => { e.stopPropagation(); window.alert('审核详情入口即将开放'); }}
                    >
                      查看详情
                    </Button>
                  )}
                  {content.status === 'published' && (
                    <Button 
                      size="sm" 
                      variant="secondary" 
                      className="flex-1"
                      onClick={(e) => { 
                        e.stopPropagation();
                        setSelectedContent(content);
                        setShowAnalytics(true);
                      }}
                    >
                      查看数据
                    </Button>
                  )}
                  {content.status === 'viral' && (
                    <Button
                      size="sm"
                      className="flex-1"
                      leftIcon={<RefreshCw className="w-3 h-3" />}
                      onClick={(e) => { e.stopPropagation(); window.alert('复用爆款入口即将开放'); }}
                    >
                      复用爆款
                    </Button>
                  )}
                  <button
                    className="p-2 rounded-lg hover:bg-accent-red/10 hover:text-accent-red transition-colors disabled:opacity-50"
                    onClick={(e) => void handleDelete(content, e)}
                    disabled={deletingId === content.id}
                    title="删除内容"
                  >
                    {deletingId === content.id ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && contents.length === 0 && (
        <div className="text-center py-20">
          <div className="w-16 h-16 rounded-full bg-background-tertiary flex items-center justify-center mx-auto mb-4">
            <FileText className="w-8 h-8 text-foreground-tertiary" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">暂无内容</h3>
          <p className="text-sm text-foreground-secondary mb-4">
            还没有{tabs.find(t => t.value === activeTab)?.label}的内容
          </p>
          <Link href="/creator/dashboard">
            <Button>去创建内容</Button>
          </Link>
        </div>
      )}

      {/* 数据分析弹窗 */}
      {showAnalytics && selectedContent && (
        <AnalyticsModal
          content={selectedContent}
          onClose={() => {
            setShowAnalytics(false);
            setSelectedContent(null);
          }}
        />
      )}
    </CreatorLayout>
  );
}

function cn(...classes: (string | undefined | false)[]): string {
  return classes.filter(Boolean).join(' ');
}

// 数据分析弹窗组件
interface AnalyticsModalProps {
  content: LibraryItem;
  onClose: () => void;
}

function AnalyticsModal({ content, onClose }: AnalyticsModalProps) {
  // 模拟4维数据（实际应从API获取）
  const metricsData = {
    completion_rate: { value: 28, status: 'warning' as const },
    like_rate: { value: 4.5, status: 'good' as const },
    comment_rate: { value: 0.6, status: 'warning' as const },
    follow_rate: { value: 0.4, status: 'danger' as const }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <Card className="relative">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-cyan-600 flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-foreground">内容数据分析</h3>
                <p className="text-sm text-foreground-secondary">4维健康度诊断</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-background-tertiary transition-colors"
            >
              <X className="w-5 h-5 text-foreground-secondary" />
            </button>
          </div>

          <div className="p-6 space-y-6">
            {/* 内容标题 */}
            <div className="p-4 bg-background-tertiary rounded-xl">
              <h4 className="font-medium text-foreground line-clamp-2">{content.title}</h4>
              <p className="text-sm text-foreground-secondary mt-1">
                发布时间: {content.publishedAt ? new Date(content.publishedAt).toLocaleString('zh-CN') : '-'}
              </p>
            </div>

            {/* 4维诊断 */}
            <div>
              <h4 className="font-semibold text-foreground mb-4 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-primary-400" />
                4维健康度诊断
              </h4>
              <div className="grid grid-cols-2 gap-4">
                {METRICS_CONFIG.map((metric) => {
                  const Icon = metric.icon;
                  const data = metricsData[metric.key as keyof typeof metricsData];
                  const isWarning = data.value < metric.threshold;
                  
                  return (
                    <div
                      key={metric.key}
                      className={`p-4 rounded-xl border ${
                        isWarning ? metric.borderColor + ' ' + metric.bgColor : 'bg-accent-green/10 border-accent-green/20'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <Icon className={`w-4 h-4 ${isWarning ? metric.color : 'text-accent-green'}`} />
                        <span className="text-sm font-medium text-foreground">{metric.name}</span>
                      </div>
                      <div className={`text-2xl font-bold mb-1 ${isWarning ? metric.color : 'text-accent-green'}`}>
                        {data.value}{metric.unit}
                      </div>
                      <div className="text-xs text-foreground-tertiary">
                        目标 ≥ {metric.threshold}{metric.unit}
                      </div>
                      {isWarning && (
                        <div className={`mt-2 text-xs ${metric.color}`}>
                          💡 {metric.suggestion}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 发布时间分析 */}
            <div>
              <h4 className="font-semibold text-foreground mb-4 flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-400" />
                发布时间分析
              </h4>
              <div className="p-4 rounded-xl bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-foreground">实际发布时间</span>
                  <span className="text-sm font-medium text-foreground">
                    {content.publishedAt ? new Date(content.publishedAt).getHours() + ':00' : '-'}
                  </span>
                </div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-foreground">建议发布时间</span>
                  <span className="text-sm font-medium text-accent-green">
                    20:00-22:00 (职场类黄金时段)
                  </span>
                </div>
                <p className="text-xs text-foreground-secondary mt-2">
                  建议下次在黄金时段发布，可获得30%+的初始流量提升
                </p>
              </div>
            </div>

            {/* 优化建议 */}
            <div>
              <h4 className="font-semibold text-foreground mb-4">优化建议</h4>
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2 text-foreground-secondary">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent-yellow mt-1.5 flex-shrink-0" />
                  完播率28%低于30%标准，建议前3秒加入强钩子
                </li>
                <li className="flex items-start gap-2 text-foreground-secondary">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent-yellow mt-1.5 flex-shrink-0" />
                  转粉率0.4%低于0.5%标准，建议结尾强化人设记忆点
                </li>
                <li className="flex items-start gap-2 text-foreground-secondary">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan mt-1.5 flex-shrink-0" />
                  点赞率4.5%表现良好，继续保持当前内容密度
                </li>
              </ul>
            </div>
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3 p-6 border-t border-border">
            <Button variant="ghost" onClick={onClose}>
              关闭
            </Button>
            <Button>
              导出报告
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
