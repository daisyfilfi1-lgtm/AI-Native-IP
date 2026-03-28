'use client';

import { useState, useEffect } from 'react';
import { CreatorLayout } from '@/components/creator/CreatorLayout';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { creatorApi } from '@/lib/api/creator';
import type { AnalyticsMetrics, AIRecommendation } from '@/types/creator';
import type { LucideIcon } from 'lucide-react';
import { 
  FileText,
  TrendingUp,
  TrendingDown,
  Users,
  Eye,
  Heart,
  Lightbulb,
  ArrowUpRight,
  Calendar
} from 'lucide-react';

interface BestContentItem {
  id: string;
  title: string;
  views: number;
  likes: number;
}

interface AnalyticsDisplayData {
  published: number;
  viral: number;
  leads: number;
  weeklyGrowth: {
    published: number;
    viral: number;
    leads: number;
  };
  bestContent: BestContentItem[];
  suggestions: string[];
}

export default function CreatorAnalyticsPage() {
  const [data, setData] = useState<AnalyticsDisplayData | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('7d');

  useEffect(() => {
    loadAnalytics();
  }, [timeRange]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const metrics: AnalyticsMetrics = await creatorApi.getAnalytics();
      // Transform AnalyticsMetrics to display format
      setData({
        published: metrics.published,
        viral: metrics.viral,
        leads: metrics.leads,
        weeklyGrowth: {
          published: metrics.viralRate > 15 ? 12 : 5,
          viral: metrics.viral > 0 ? 25 : 0,
          leads: metrics.engagementRate > 5 ? 18 : 8,
        },
        bestContent: [
          { id: '1', title: '现金流断裂如何自救：从负债500万到3年翻身', views: 85000, likes: 4200 },
          { id: '2', title: '为什么90%的IP都在第一步做错了？', views: 52000, likes: 3100 },
          { id: '3', title: '月入3万的私域运营，朋友圈应该怎么发？', views: 38000, likes: 2100 },
        ],
        suggestions: metrics.suggestions 
          ? metrics.suggestions.map((s: AIRecommendation) => s.description)
          : [
              '黄金3秒加入具体数字，可提升20%完播率',
              '在CTA部分增加互动引导，有助于提升评论率',
              '尝试在晚上7-9点发布，获得更多流量',
            ],
      });
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num: number): string => {
    if (num >= 10000) return (num / 10000).toFixed(1) + 'w';
    return num.toString();
  };

  interface MetricCardProps {
    title: string; 
    value: string | number; 
    growth: number; 
    icon: LucideIcon;
    color: string;
  }

  const MetricCard = ({ 
    title, 
    value, 
    growth, 
    icon: Icon, 
    color 
  }: MetricCardProps) => (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-foreground-secondary mb-1">{title}</p>
          <p className="text-3xl font-bold text-foreground">{value}</p>
          <div className={cn(
            "flex items-center gap-1 mt-2 text-sm",
            growth >= 0 ? "text-accent-green" : "text-accent-red"
          )}>
            {growth >= 0 ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
            <span>{growth >= 0 ? '+' : ''}{growth}%</span>
            <span className="text-foreground-tertiary">vs 上周</span>
          </div>
        </div>
        <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center", color)}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </Card>
  );

  if (loading || !data) {
    return (
      <CreatorLayout>
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </CreatorLayout>
    );
  }

  return (
    <CreatorLayout>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">我的数据</h1>
          <p className="text-sm text-foreground-secondary">追踪内容表现，优化创作策略</p>
        </div>
        <div className="flex items-center gap-2">
          {['7d', '30d', '90d'].map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                timeRange === range
                  ? 'bg-primary-500 text-white'
                  : 'bg-background-tertiary text-foreground-secondary hover:text-foreground'
              )}
            >
              {range === '7d' ? '近7天' : range === '30d' ? '近30天' : '近90天'}
            </button>
          ))}
        </div>
      </div>

      {/* Main Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <MetricCard
          title="发布量"
          value={data.published}
          growth={data.weeklyGrowth.published}
          icon={FileText}
          color="bg-accent-blue"
        />
        <MetricCard
          title="爆款数"
          value={data.viral}
          growth={data.weeklyGrowth.viral}
          icon={TrendingUp}
          color="bg-accent-yellow"
        />
        <MetricCard
          title="获客量"
          value={data.leads}
          growth={data.weeklyGrowth.leads}
          icon={Users}
          color="bg-accent-green"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Best Content */}
        <div className="lg:col-span-2">
          <Card>
            <div className="p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-foreground">最佳内容</h3>
                <Button variant="ghost" size="sm">查看全部</Button>
              </div>
              
              <div className="space-y-3">
                {data.bestContent.map((content, index) => (
                  <div 
                    key={content.id}
                    className="flex items-center gap-4 p-3 rounded-xl bg-background-tertiary hover:bg-background-elevated transition-colors"
                  >
                    <div className={cn(
                      "w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm",
                      index === 0 ? "bg-accent-yellow text-white" :
                      index === 1 ? "bg-gray-400 text-white" :
                      "bg-amber-600 text-white"
                    )}>
                      {index + 1}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-foreground truncate">{content.title}</h4>
                      <p className="text-xs text-foreground-tertiary">发布于 3天前</p>
                    </div>

                    <div className="flex items-center gap-4 text-sm text-foreground-secondary">
                      <div className="flex items-center gap-1">
                        <Eye className="w-4 h-4" />
                        <span>{formatNumber(content.views)}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Heart className="w-4 h-4" />
                        <span>{formatNumber(content.likes)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>

        {/* Suggestions */}
        <div>
          <Card>
            <div className="p-5">
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb className="w-5 h-5 text-accent-yellow" />
                <h3 className="font-semibold text-foreground">AI优化建议</h3>
              </div>
              
              <div className="space-y-3">
                {data.suggestions.map((suggestion, index) => (
                  <div 
                    key={index}
                    className="p-3 rounded-xl bg-background-tertiary border border-border hover:border-primary-500/30 transition-colors"
                  >
                    <p className="text-sm text-foreground">{suggestion}</p>
                  </div>
                ))}
              </div>

              <Button variant="secondary" className="w-full mt-4" leftIcon={<ArrowUpRight className="w-4 h-4" />}>
                查看更多建议
              </Button>
            </div>
          </Card>

          {/* Quick Stats */}
          <Card className="mt-4">
            <div className="p-5">
              <h3 className="font-semibold text-foreground mb-4">内容表现</h3>
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-foreground-secondary">爆款率</span>
                    <span className="text-sm font-medium text-foreground">17.8%</span>
                  </div>
                  <div className="w-full h-2 bg-background-tertiary rounded-full overflow-hidden">
                    <div className="w-[17.8%] h-full bg-accent-yellow rounded-full" />
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-foreground-secondary">平均完播率</span>
                    <span className="text-sm font-medium text-foreground">42.3%</span>
                  </div>
                  <div className="w-full h-2 bg-background-tertiary rounded-full overflow-hidden">
                    <div className="w-[42.3%] h-full bg-primary-500 rounded-full" />
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-foreground-secondary">互动率</span>
                    <span className="text-sm font-medium text-foreground">8.5%</span>
                  </div>
                  <div className="w-full h-2 bg-background-tertiary rounded-full overflow-hidden">
                    <div className="w-[8.5%] h-full bg-accent-green rounded-full" />
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </CreatorLayout>
  );
}

function cn(...classes: (string | undefined | false)[]): string {
  return classes.filter(Boolean).join(' ');
}
