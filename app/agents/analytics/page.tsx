'use client';

import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { Select } from '@/components/ui/Select';
import { Progress } from '@/components/ui/Progress';
import { 
  BarChart3, 
  TrendingUp, 
  TrendingDown, 
  Eye,
  Heart,
  MessageCircle,
  Share2,
  Download,
  Clock,
  Users,
  AlertCircle,
  CheckCircle2,
  Lightbulb,
  ThumbsUp,
  MessageSquare,
  Target
} from 'lucide-react';

// 数据反馈维度诊断标准
const METRICS_DIAGNOSIS = [
  {
    key: 'completion_rate',
    name: '完播率',
    icon: Clock,
    threshold: 30,
    unit: '%',
    suggestion: '需优化开头钩子',
    color: 'text-accent-cyan',
    bgColor: 'bg-accent-cyan/10',
    borderColor: 'border-accent-cyan/20',
    description: '用户观看完整视频的比例'
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
    borderColor: 'border-accent-pink/20',
    description: '点赞数 / 播放数'
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
    borderColor: 'border-accent-yellow/20',
    description: '评论数 / 播放数'
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
    borderColor: 'border-accent-green/20',
    description: '新增粉丝 / 播放数'
  }
];

// 黄金发布时间配置
const PUBLISH_TIME_RECOMMENDATIONS = [
  {
    category: '职场类',
    emoji: '💼',
    times: [
      { period: '早高峰', time: '8:00-9:00', desc: '通勤时间，碎片化阅读' },
      { period: '午休', time: '12:00-13:00', desc: '饭后休闲，刷视频高峰' },
      { period: '晚间', time: '20:00-22:00', desc: '下班放松，深度内容消费' }
    ],
    color: 'from-blue-500 to-cyan-500'
  },
  {
    category: '育儿类',
    emoji: '👶',
    times: [
      { period: '早晨', time: '7:00-8:00', desc: '孩子起床前，妈妈准备时间' },
      { period: '晚间', time: '19:00-21:00', desc: '孩子入睡后，妈妈自由时间' }
    ],
    color: 'from-pink-500 to-rose-500'
  },
  {
    category: '知识类',
    emoji: '📚',
    times: [
      { period: '下午', time: '14:00-16:00', desc: '工作间隙，学习充电' },
      { period: '深夜', time: '21:00-23:00', desc: '睡前学习，自我提升时间' }
    ],
    color: 'from-purple-500 to-indigo-500'
  }
];

// 模拟数据 - 用于展示诊断结果
const MOCK_METRICS_DATA = {
  completion_rate: { value: 25, status: 'warning' },
  like_rate: { value: 4.2, status: 'good' },
  comment_rate: { value: 0.8, status: 'warning' },
  follow_rate: { value: 0.3, status: 'danger' }
};

export default function AnalyticsAgentPage() {
  return (
    <MainLayout title="分析Agent - 配置">
      <div className="mb-6 p-6 rounded-2xl bg-gradient-to-r from-purple-500/10 to-cyan-600/10 border border-purple-500/20">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-500 to-cyan-600 flex items-center justify-center text-2xl">
            📊
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-foreground">分析Agent</h2>
            <p className="text-foreground-secondary">自动化数据归因与策略迭代，4维数据诊断 + 黄金发布时间优化</p>
          </div>
          <Badge variant="success" dot>运行中</Badge>
        </div>
      </div>

      <Tabs defaultValue="diagnosis" className="w-full">
        <TabsList>
          <TabsTrigger value="diagnosis">4维数据诊断</TabsTrigger>
          <TabsTrigger value="publish_time">黄金发布时间</TabsTrigger>
          <TabsTrigger value="overview">数据概览</TabsTrigger>
          <TabsTrigger value="attribution">归因分析</TabsTrigger>
          <TabsTrigger value="config">配置</TabsTrigger>
        </TabsList>

        {/* 4维数据诊断 */}
        <TabsContent value="diagnosis">
          <div className="space-y-6">
            {/* 诊断说明 */}
            <div className="p-4 bg-gradient-to-r from-primary-500/10 to-accent-cyan/10 rounded-xl border border-primary-500/20">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-500 to-accent-cyan flex items-center justify-center">
                  <Target className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-medium text-foreground mb-1">内容健康度4维诊断</h3>
                  <p className="text-sm text-foreground-secondary">
                    基于行业标准和你的历史数据，自动诊断内容问题并给出优化建议
                  </p>
                </div>
              </div>
            </div>

            {/* 4个维度卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {METRICS_DIAGNOSIS.map((metric) => {
                const Icon = metric.icon;
                const data = MOCK_METRICS_DATA[metric.key as keyof typeof MOCK_METRICS_DATA];
                const isWarning = data.value < metric.threshold;
                
                return (
                  <Card key={metric.key} className={`overflow-hidden ${isWarning ? 'border-accent-yellow/50' : ''}`}>
                    <div className="p-5">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-12 h-12 rounded-xl ${metric.bgColor} flex items-center justify-center`}>
                            <Icon className={`w-6 h-6 ${metric.color}`} />
                          </div>
                          <div>
                            <h4 className="font-semibold text-foreground">{metric.name}</h4>
                            <p className="text-xs text-foreground-tertiary">{metric.description}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`text-2xl font-bold ${isWarning ? 'text-accent-yellow' : 'text-accent-green'}`}>
                            {data.value}{metric.unit}
                          </div>
                          <div className="text-xs text-foreground-tertiary">
                            目标 ≥ {metric.threshold}{metric.unit}
                          </div>
                        </div>
                      </div>

                      {/* 进度条 */}
                      <div className="mb-4">
                        <Progress 
                          value={(data.value / (metric.threshold * 2)) * 100} 
                          size="sm"
                          variant={isWarning ? 'warning' : 'success'}
                        />
                      </div>

                      {/* 诊断结果 */}
                      <div className={`p-3 rounded-xl ${isWarning ? metric.bgColor + ' ' + metric.borderColor + ' border' : 'bg-accent-green/10 border border-accent-green/20'}`}>
                        <div className="flex items-center gap-2">
                          {isWarning ? (
                            <AlertCircle className={`w-4 h-4 ${metric.color}`} />
                          ) : (
                            <CheckCircle2 className="w-4 h-4 text-accent-green" />
                          )}
                          <span className={`text-sm font-medium ${isWarning ? metric.color : 'text-accent-green'}`}>
                            {isWarning ? metric.suggestion : '表现良好，继续保持'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>

            {/* 优化建议汇总 */}
            <Card>
              <CardHeader 
                title="优化建议汇总" 
                description="基于当前数据表现，AI给出的优化建议"
              />
              <div className="space-y-3">
                <div className="p-4 rounded-xl bg-accent-yellow/10 border border-accent-yellow/20">
                  <div className="flex items-start gap-3">
                    <Lightbulb className="w-5 h-5 text-accent-yellow flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-foreground mb-1">优先级优化</h4>
                      <ul className="space-y-2 text-sm text-foreground-secondary">
                        <li>• 完播率25%低于30%标准，建议前3秒加入强钩子（如争议观点/惊人数字）</li>
                        <li>• 转粉率0.3%低于0.5%标准，建议在结尾强化人设记忆点（如固定slogan）</li>
                        <li>• 评论率0.8%接近1%标准，可适当增加争议性话题引导互动</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>

        {/* 黄金发布时间 */}
        <TabsContent value="publish_time">
          <div className="space-y-6">
            {/* 说明 */}
            <div className="p-4 bg-gradient-to-r from-amber-500/10 to-orange-500/10 rounded-xl border border-amber-500/20">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
                  <Clock className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-medium text-foreground mb-1">黄金发布时间</h3>
                  <p className="text-sm text-foreground-secondary">
                    基于内容类别和目标受众，选择最佳发布时间以获取更多流量
                  </p>
                </div>
              </div>
            </div>

            {/* 时间推荐卡片 */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {PUBLISH_TIME_RECOMMENDATIONS.map((category) => (
                <Card key={category.category} className="overflow-hidden">
                  {/* 头部 */}
                  <div className={`p-4 bg-gradient-to-r ${category.color} text-white`}>
                    <div className="flex items-center gap-3">
                      <span className="text-3xl">{category.emoji}</span>
                      <h3 className="text-lg font-bold">{category.category}</h3>
                    </div>
                  </div>

                  {/* 时间段列表 */}
                  <div className="p-4 space-y-3">
                    {category.times.map((time, index) => (
                      <div key={index} className="p-3 rounded-xl bg-background-tertiary border border-border hover:border-primary-500/30 transition-colors">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-foreground">{time.period}</span>
                          <Badge variant="primary" size="sm">{time.time}</Badge>
                        </div>
                        <p className="text-xs text-foreground-secondary">{time.desc}</p>
                      </div>
                    ))}
                  </div>
                </Card>
              ))}
            </div>

            {/* IP类型自动匹配 */}
            <Card>
              <CardHeader 
                title="智能时间匹配" 
                description="根据你的IP内容方向自动推荐发布时间"
              />
              <div className="space-y-3">
                <div className="p-4 rounded-xl bg-background-tertiary border border-border">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">💼</span>
                      <span className="font-medium text-foreground">职场成长类内容</span>
                    </div>
                    <Badge variant="success" size="sm">已匹配</Badge>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {['8:00-9:00', '12:00-13:00', '20:00-22:00'].map((time) => (
                      <span key={time} className="px-3 py-1.5 rounded-lg bg-primary-500/10 text-primary-400 text-sm">
                        <Clock className="w-3 h-3 inline mr-1" />
                        {time}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="overview">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <Card>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary-500/10 flex items-center justify-center">
                  <Eye className="w-5 h-5 text-primary-400" />
                </div>
                <div>
                  <p className="text-2xs text-foreground-tertiary uppercase">总播放量</p>
                  <p className="text-xl font-bold text-foreground">128.5K</p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-accent-pink/10 flex items-center justify-center">
                  <Heart className="w-5 h-5 text-accent-pink" />
                </div>
                <div>
                  <p className="text-2xs text-foreground-tertiary uppercase">点赞数</p>
                  <p className="text-xl font-bold text-foreground">8.2K</p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-accent-cyan/10 flex items-center justify-center">
                  <MessageCircle className="w-5 h-5 text-accent-cyan" />
                </div>
                <div>
                  <p className="text-2xs text-foreground-tertiary uppercase">评论数</p>
                  <p className="text-xl font-bold text-foreground">1.5K</p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-accent-green/10 flex items-center justify-center">
                  <Users className="w-5 h-5 text-accent-green" />
                </div>
                <div>
                  <p className="text-2xs text-foreground-tertiary uppercase">新增粉丝</p>
                  <p className="text-xl font-bold text-foreground">856</p>
                </div>
              </div>
            </Card>
          </div>

          <Card>
            <CardHeader title="趋势分析" description="近7天播放量趋势" />
            <div className="h-64 flex items-center justify-center bg-background-tertiary rounded-xl">
              <div className="text-center">
                <BarChart3 className="w-12 h-12 mx-auto mb-2 text-foreground-tertiary" />
                <p className="text-sm text-foreground-secondary">图表将在此显示</p>
              </div>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="attribution">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader title="成功因素分析" description="内容成功的关键因素占比" />
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-accent-green/10 border border-accent-green/20">
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingUp className="w-5 h-5 text-accent-green" />
                    <span className="font-medium text-accent-green">因素占比</span>
                  </div>
                  <div className="space-y-3">
                    {[
                      { name: '选题吸引力', value: 35, color: 'bg-primary-500' },
                      { name: '黄金3秒钩子', value: 25, color: 'bg-accent-pink' },
                      { name: '内容质量', value: 20, color: 'bg-accent-cyan' },
                      { name: '发布时间', value: 15, color: 'bg-accent-yellow' },
                      { name: '其他因素', value: 5, color: 'bg-foreground-muted' },
                    ].map((item) => (
                      <div key={item.name}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-foreground">{item.name}</span>
                          <Badge variant="success" size="sm">{item.value}%</Badge>
                        </div>
                        <div className="w-full h-2 bg-background-elevated rounded-full overflow-hidden">
                          <div className={`h-full ${item.color} rounded-full`} style={{ width: `${item.value}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader title="改进建议" description="针对低表现内容的优化方向" />
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-accent-red/10 border border-accent-red/20">
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingDown className="w-5 h-5 text-accent-red" />
                    <span className="font-medium text-accent-red">优化方向</span>
                  </div>
                  <ul className="space-y-3 text-sm text-foreground-secondary">
                    <li className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-accent-red mt-1.5 flex-shrink-0" />
                      <span>优化开头钩子，在黄金3秒抓住注意力</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-accent-red mt-1.5 flex-shrink-0" />
                      <span>控制视频时长在45秒内，提升完播率</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-accent-red mt-1.5 flex-shrink-0" />
                      <span>增加情绪转折点，保持观众注意力</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-accent-red mt-1.5 flex-shrink-0" />
                      <span>选择合适的发布时间，匹配目标受众活跃时段</span>
                    </li>
                  </ul>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="config">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader title="诊断阈值配置" description="自定义4维诊断的健康标准" />
              <div className="space-y-5">
                {METRICS_DIAGNOSIS.map((metric) => (
                  <div key={metric.key}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <metric.icon className={`w-4 h-4 ${metric.color}`} />
                        <span className="text-sm text-foreground">{metric.name}</span>
                      </div>
                      <span className="text-sm font-medium text-foreground">≥ {metric.threshold}{metric.unit}</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max={metric.threshold * 2}
                      defaultValue={metric.threshold}
                      className="w-full h-2 bg-background-elevated rounded-lg appearance-none cursor-pointer accent-primary-500"
                    />
                    <p className="text-xs text-foreground-tertiary mt-1">低于此值将触发优化建议</p>
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader title="告警阈值" description="数据异常时发送通知" />
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-foreground">单条内容播放量</span>
                    <span className="text-sm font-medium text-foreground">{'< 500'}</span>
                  </div>
                  <input
                    type="range"
                    min="100"
                    max="2000"
                    defaultValue="500"
                    className="w-full h-2 bg-background-elevated rounded-lg appearance-none cursor-pointer accent-primary-500"
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-foreground">连续低迷内容数</span>
                    <span className="text-sm font-medium text-foreground">{'≥ 3条'}</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    defaultValue="3"
                    className="w-full h-2 bg-background-elevated rounded-lg appearance-none cursor-pointer accent-primary-500"
                  />
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </MainLayout>
  );
}
