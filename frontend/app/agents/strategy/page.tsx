'use client';

import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Switch } from '@/components/ui/Switch';
import { 
  GitBranch, 
  Search, 
  Target, 
  Settings,
  Plus,
  Trash2,
  TrendingUp,
  Lightbulb,
  Flame,
  Users,
  AlertTriangle,
  Sparkles
} from 'lucide-react';

// 八大爆款元素配置
const VIRAL_ELEMENTS = [
  { id: 'cost', name: '成本', emoji: '💰', desc: '低成本/高成本', example: '"10元做出米其林口感"', color: 'from-green-500 to-emerald-500' },
  { id: 'crowd', name: '人群', emoji: '👥', desc: '细分/特定人群', example: '"90后宝妈避坑指南"', color: 'from-blue-500 to-cyan-500' },
  { id: 'weird', name: '奇葩', emoji: '🤪', desc: '反常/猎奇', example: '"月入3千比3万过得好"', color: 'from-purple-500 to-pink-500' },
  { id: 'worst', name: '最差', emoji: '⛔', desc: '避坑/负面', example: '"千万别买的5种家电"', color: 'from-red-500 to-orange-500' },
  { id: 'contrast', name: '反差', emoji: '🔄', desc: '前后对比', example: '"改造前vs改造后"', color: 'from-yellow-500 to-amber-500' },
  { id: 'nostalgia', name: '怀旧', emoji: '📷', desc: '情感共鸣', example: '"80后才懂的零食"', color: 'from-indigo-500 to-purple-500' },
  { id: 'hormone', name: '荷尔蒙', emoji: '💖', desc: '颜值/情感', example: '"初恋脸养成日记"', color: 'from-pink-500 to-rose-500' },
  { id: 'top', name: '头牌', emoji: '👑', desc: '第一/权威', example: '"行业第一的选品逻辑"', color: 'from-amber-500 to-yellow-500' },
];

export default function StrategyAgentPage() {
  return (
    <MainLayout title="策略Agent - 配置">
      {/* Agent header */}
      <div className="mb-6 p-6 rounded-2xl bg-gradient-to-r from-cyan-500/10 to-blue-600/10 border border-cyan-500/20">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-2xl">
            🎯
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-foreground">策略Agent</h2>
            <p className="text-foreground-secondary">决策内容选题和投放策略，八大爆款元素智能匹配</p>
          </div>
          <Badge variant="success" dot>运行中</Badge>
        </div>
      </div>

      <Tabs defaultValue="topics" className="w-full">
        <TabsList>
          <TabsTrigger value="topics">选题推荐</TabsTrigger>
          <TabsTrigger value="viral">八大爆款元素</TabsTrigger>
          <TabsTrigger value="scoring">选题评分卡</TabsTrigger>
          <TabsTrigger value="competitors">竞品监控</TabsTrigger>
          <TabsTrigger value="config">高级配置</TabsTrigger>
        </TabsList>

        <TabsContent value="topics">
          <Card>
            <CardHeader 
              title="今日选题推荐" 
              description="基于热点数据、八大爆款元素和IP契合度智能推荐"
              action={<Button size="sm" leftIcon={<Search className="w-4 h-4" />}>刷新</Button>}
            />
            <div className="space-y-3">
              {[
                { title: '创业者如何度过低谷期', score: 95, trend: 'up', reason: '低粉爆款，情绪共鸣强', elements: ['crowd', 'nostalgia', 'contrast'] },
                { title: '2026年AI创业新机会', score: 88, trend: 'up', reason: '热点话题，搜索量激增', elements: ['top', 'weird'] },
                { title: '从0到1打造个人IP', score: 82, trend: 'stable', reason: '经典话题， evergreen', elements: ['cost', 'contrast', 'top'] },
              ].map((topic, index) => (
                <div key={index} className="p-4 rounded-xl bg-background-tertiary border border-border">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-medium text-foreground">{topic.title}</h4>
                        <Badge variant={topic.score >= 90 ? 'success' : 'primary'} size="sm">
                          {topic.score}分
                        </Badge>
                      </div>
                      <p className="text-sm text-foreground-secondary mb-2">{topic.reason}</p>
                      {/* 爆款元素标签 */}
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs text-foreground-tertiary">匹配元素:</span>
                        {topic.elements.map((elemId) => {
                          const elem = VIRAL_ELEMENTS.find(e => e.id === elemId);
                          return elem ? (
                            <span key={elemId} className="text-xs px-1.5 py-0.5 bg-background-elevated rounded">
                              {elem.emoji} {elem.name}
                            </span>
                          ) : null;
                        })}
                      </div>
                    </div>
                    <Button variant="secondary" size="sm">生成内容</Button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>

        {/* 八大爆款元素配置 */}
        <TabsContent value="viral">
          <div className="space-y-6">
            {/* 八大元素说明 */}
            <div className="p-4 bg-gradient-to-r from-orange-500/10 to-red-500/10 rounded-xl border border-orange-500/20">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
                  <Flame className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-medium text-foreground mb-1">八大爆款元素</h3>
                  <p className="text-sm text-foreground-secondary">
                    每条选题需融入<span className="text-orange-400">2-3个爆款元素</span>，
                    AI会自动分析选题中的爆款潜力，并在生成时强化这些元素的表现。
                  </p>
                </div>
              </div>
            </div>

            {/* 元素网格 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {VIRAL_ELEMENTS.map((element) => (
                <Card key={element.id} className="overflow-hidden">
                  <div className="p-4">
                    <div className="flex items-start gap-4">
                      {/* 图标 */}
                      <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${element.color} flex items-center justify-center flex-shrink-0`}>
                        <span className="text-2xl">{element.emoji}</span>
                      </div>
                      
                      {/* 内容 */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <h4 className="font-semibold text-foreground">{element.name}</h4>
                          <Switch defaultChecked size={20} />
                        </div>
                        <p className="text-sm text-foreground-secondary mb-2">{element.desc}</p>
                        
                        {/* 案例 */}
                        <div className="p-2 bg-background-tertiary rounded-lg">
                          <span className="text-xs text-foreground-tertiary">案例: </span>
                          <span className="text-sm text-foreground">{element.example}</span>
                        </div>

                        {/* 使用频率 */}
                        <div className="mt-3">
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="text-foreground-tertiary">使用频率</span>
                            <span className="text-foreground">推荐</span>
                          </div>
                          <div className="flex gap-1">
                            {['低', '中', '高'].map((level, i) => (
                              <button
                                key={level}
                                className={`flex-1 py-1 text-xs rounded ${
                                  i === 1 
                                    ? 'bg-primary-500 text-white' 
                                    : 'bg-background-tertiary text-foreground-secondary hover:bg-background-elevated'
                                }`}
                              >
                                {level}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>

            {/* 元素组合推荐 */}
            <Card>
              <CardHeader 
                title="高转化元素组合" 
                description="基于数据分析的高效组合推荐"
              />
              <div className="space-y-3">
                {[
                  { elements: ['cost', 'contrast', 'crowd'], desc: '省钱技巧类，完播率高', rate: '92%' },
                  { elements: ['nostalgia', 'hormone', 'weird'], desc: '情感共鸣类，互动率高', rate: '88%' },
                  { elements: ['worst', 'top', 'crowd'], desc: '避坑指南类，转化率高', rate: '85%' },
                ].map((combo, index) => (
                  <div key={index} className="flex items-center justify-between p-3 rounded-xl bg-background-tertiary">
                    <div className="flex items-center gap-2">
                      {combo.elements.map((elemId) => {
                        const elem = VIRAL_ELEMENTS.find(e => e.id === elemId);
                        return elem ? (
                          <span key={elemId} className="text-lg" title={elem.name}>{elem.emoji}</span>
                        ) : null;
                      })}
                      <span className="text-sm text-foreground-secondary ml-2">{combo.desc}</span>
                    </div>
                    <Badge variant="success" size="sm">爆款率 {combo.rate}</Badge>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </TabsContent>

        {/* 选题评分卡 */}
        <TabsContent value="scoring">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader 
                title="选题评分卡" 
                description="≥7分才执行拍摄（每项最高2分）" 
              />
              <div className="space-y-5">
                {[
                  { name: '目标人群精准度', key: 'target', value: 2, desc: '是否精准打击目标受众', max: 2 },
                  { name: '痛点强度', key: 'pain', value: 2, desc: '痛点是否足够痛', max: 2 },
                  { name: '爆款元素数量', key: 'viral', value: 2, desc: '包含2-3个元素得2分', max: 3 },
                  { name: '制作难度', key: 'cost', value: 0, desc: '简单+1分，复杂-1分', max: 1, min: -1 },
                  { name: '变现关联度', key: 'monetization', value: 2, desc: '与产品/服务的关联', max: 2 },
                ].map((item) => (
                  <div key={item.key}>
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <span className="font-medium text-foreground">{item.name}</span>
                        <p className="text-xs text-foreground-tertiary">{item.desc}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-foreground">{item.value}分</span>
                        <span className="text-xs text-foreground-muted">/ {item.max}分</span>
                      </div>
                    </div>
                    <input
                      type="range"
                      min={item.min || 0}
                      max={item.max}
                      step={item.key === 'cost' ? 1 : 1}
                      defaultValue={item.value}
                      className="w-full h-2 bg-background-elevated rounded-lg appearance-none cursor-pointer accent-primary-500"
                    />
                  </div>
                ))}

                {/* 总分显示 */}
                <div className="p-4 bg-gradient-to-r from-primary-500/10 to-accent-cyan/10 rounded-xl border border-primary-500/20">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-foreground">选题总分</span>
                    <div className="flex items-center gap-2">
                      <span className="text-2xl font-bold text-primary-400">8</span>
                      <span className="text-foreground-muted">/ 10分</span>
                      <Badge variant="success">可拍摄</Badge>
                    </div>
                  </div>
                  <p className="text-xs text-foreground-secondary mt-2">
                    评分标准：≥7分建议拍摄，5-6分可尝试，&lt;5分建议放弃
                  </p>
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader title="四维评分权重" description="调节四个维度的权重占比" />
              <div className="space-y-6">
                {[
                  { name: '流量潜力', key: 'traffic', value: 30, description: '话题热度和搜索量' },
                  { name: '变现关联', key: 'monetization', value: 30, description: '与产品/服务的关联度' },
                  { name: 'IP契合度', key: 'fit', value: 25, description: '与IP人设的匹配程度' },
                  { name: '制作成本', key: 'cost', value: 15, description: '内容制作的时间和资源成本' },
                ].map((item) => (
                  <div key={item.key}>
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <span className="font-medium text-foreground">{item.name}</span>
                        <p className="text-xs text-foreground-tertiary">{item.description}</p>
                      </div>
                      <span className="text-sm font-medium text-foreground">{item.value}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      defaultValue={item.value}
                      className="w-full h-2 bg-background-elevated rounded-lg appearance-none cursor-pointer accent-primary-500"
                    />
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="competitors">
          <Card>
            <CardHeader 
              title="竞品监控清单" 
              description="监控以下账号的爆款内容"
              action={<Button size="sm" leftIcon={<Plus className="w-4 h-4" />}>添加</Button>}
            />
            <div className="space-y-3">
              {[
                { name: '张琦商业思维', platform: '抖音', followers: '850万' },
                { name: '参哥认知圈', platform: '抖音', followers: '620万' },
                { name: '大齐商业人性', platform: '视频号', followers: '180万' },
              ].map((competitor, index) => (
                <div key={index} className="flex items-center justify-between p-3 rounded-xl bg-background-tertiary">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold">
                      {competitor.name[0]}
                    </div>
                    <div>
                      <p className="font-medium text-foreground">{competitor.name}</p>
                      <p className="text-xs text-foreground-tertiary">{competitor.platform} · {competitor.followers}粉丝</p>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm" leftIcon={<Trash2 className="w-4 h-4" />}>
                    移除
                  </Button>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="config">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader title="抓取配置" description="竞品数据抓取设置" />
              <div className="space-y-4">
                <Select
                  label="监控频率"
                  options={[
                    { value: '15min', label: '每15分钟' },
                    { value: '1hour', label: '每小时' },
                    { value: '6hours', label: '每6小时' },
                    { value: 'daily', label: '每天' },
                  ]}
                />
                <Input
                  label="爆款阈值（点赞数）"
                  type="number"
                  defaultValue="10000"
                  helper="低粉账号的爆款判定标准"
                />
                <Switch 
                  label="自动抓取" 
                  description="开启后自动监控竞品更新"
                  defaultChecked
                />
              </div>
            </Card>

            <Card>
              <CardHeader title="选题黑名单" description="设置绝不触碰的话题" />
              <div className="space-y-3">
                {['政治', '宗教', '医疗', '竞品名称'].map((item) => (
                  <div key={item} className="flex items-center justify-between p-3 rounded-xl bg-background-tertiary">
                    <span className="text-foreground">{item}</span>
                    <Button variant="ghost" size="sm" leftIcon={<Trash2 className="w-4 h-4" />}>
                      移除
                    </Button>
                  </div>
                ))}
                <Button variant="secondary" size="sm" className="w-full" leftIcon={<Plus className="w-4 h-4" />}>
                  添加关键词
                </Button>
              </div>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </MainLayout>
  );
}
