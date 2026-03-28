'use client';

import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { 
  Shuffle, 
  Link as LinkIcon, 
  Scissors, 
  CheckCircle2,
  Play,
  Lightbulb,
  RefreshCw,
  FileText,
  Brain,
  Heart,
  AlertTriangle,
  TrendingUp,
  BookOpen,
  Wand2
} from 'lucide-react';

// 四大黄金脚本模板
const SCRIPT_TEMPLATES = [
  {
    id: 'opinion',
    name: '说观点',
    emoji: '💡',
    desc: '吸真粉/高互动',
    structure: [
      { part: '钩子', duration: '3秒', desc: '争议性观点', example: '"90%的人不知道，努力是职场最大的陷阱"' },
      { part: '论据', duration: '30秒', desc: '3个维度证明（数据/案例/逻辑）', example: '第一，数据显示...第二，真实案例...第三，逻辑推导...' },
      { part: '升华', duration: '5秒', desc: '情感共鸣+引导互动', example: '"你同意吗？评论区见"' },
    ],
    keywords: ['我认为', '真相是', '揭秘', '说白了'],
    bestFor: '建立专业人设，引发评论区讨论',
    color: 'from-yellow-500 to-amber-500',
    bgColor: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500/20'
  },
  {
    id: 'process',
    name: '晒过程',
    emoji: '🎬',
    desc: '强转化/近变现',
    structure: [
      { part: '钩子', duration: '3秒', desc: '十大勾子技巧', example: '"花5000元买的教训"' },
      { part: '过程', duration: '40秒', desc: '服务/产品交付全过程', example: '第一步...第二步...最关键的一步...' },
      { part: '结果', duration: '7秒', desc: '成果展示+CTA', example: '"这就是专业，需要同款服务私信我"' },
    ],
    contentTypes: ['过程展示', '产品测评', '任务挑战', '事件体验'],
    hookTechniques: ['反常识开头', '进度条预告', '身份悬念', '花X元买的教训'],
    bestFor: '展示服务/产品交付过程，建立信任促成交',
    color: 'from-green-500 to-emerald-500',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/20'
  },
  {
    id: 'knowledge',
    name: '教知识',
    emoji: '📚',
    desc: '精准粉/高客单',
    structure: [
      { part: '问题', duration: '5秒', desc: '具体问题或痛点', example: '"Excel去重总是出错？"' },
      { part: '方法', duration: '35秒', desc: '步骤详解', example: '首先...然后...注意这个关键点...' },
      { part: '总结', duration: '5秒', desc: '价值强化+引导', example: '"学会了点个赞，想要更多技巧关注我"' },
    ],
    topicMethods: ['解题型', '案例型', '推荐型', '揭秘型', '颠覆型'],
    keywords: ['三步教你', '核心技巧', '必须知道', '干货'],
    bestFor: '知识付费引流，筛选高意向用户',
    color: 'from-blue-500 to-cyan-500',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/20'
  },
  {
    id: 'story',
    name: '讲故事',
    emoji: '📖',
    desc: '立人设/高信任',
    structure: [
      { part: '困境', duration: '15秒', desc: '建立共情', example: '"2022年，我的公司现金流断裂..."' },
      { part: '转折', duration: '10秒', desc: '点燃希望', example: '"但一个数据让我改变了想法..."' },
      { part: '方法', duration: '20秒', desc: '提供价值', example: '"我做对了这三件事..."' },
      { part: '结果', duration: '5秒', desc: '结果证明', example: '"3年后，我还清了所有债务"' },
    ],
    prototypes: ['小有成就型', '平凡英雄型', '重新成功型'],
    emotionCurve: '困境(共情) → 转折(希望) → 方法(价值) → 结果(证明)',
    bestFor: '高客单产品成交前，建立深度情感连接',
    color: 'from-purple-500 to-pink-500',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/20'
  },
];

export default function RemixAgentPage() {
  return (
    <MainLayout title="重组Agent - 配置">
      {/* Agent header */}
      <div className="mb-6 p-6 rounded-2xl bg-gradient-to-r from-pink-500/10 to-rose-600/10 border border-pink-500/20">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-pink-500 to-rose-600 flex items-center justify-center text-2xl">
            🔀
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-foreground">重组Agent</h2>
            <p className="text-foreground-secondary">竞品解构并IP化重组，四大黄金脚本模板智能匹配</p>
          </div>
          <Badge variant="success" dot>运行中</Badge>
        </div>
      </div>

      <Tabs defaultValue="templates" className="w-full">
        <TabsList>
          <TabsTrigger value="templates">四大脚本模板</TabsTrigger>
          <TabsTrigger value="deconstruct">竞品解构</TabsTrigger>
          <TabsTrigger value="remix">内容重组</TabsTrigger>
          <TabsTrigger value="rules">重组规则</TabsTrigger>
          <TabsTrigger value="config">高级配置</TabsTrigger>
        </TabsList>

        {/* 四大脚本模板 */}
        <TabsContent value="templates">
          <div className="space-y-6">
            {/* 说明 */}
            <div className="p-4 bg-gradient-to-r from-amber-500/10 to-orange-500/10 rounded-xl border border-amber-500/20">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-medium text-foreground mb-1">四大黄金脚本模板</h3>
                  <p className="text-sm text-foreground-secondary">
                    所有爆款内容都可归类为这<span className="text-amber-400">四种脚本模型</span>。
                    AI会自动识别竞品使用的模板类型，并在重组时为你匹配最适合的模板结构。
                  </p>
                </div>
              </div>
            </div>

            {/* 模板卡片 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {SCRIPT_TEMPLATES.map((template) => (
                <Card key={template.id} className="overflow-hidden">
                  {/* 头部 */}
                  <div className={`p-4 ${template.bgColor} border-b ${template.borderColor}`}>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${template.color} flex items-center justify-center`}>
                          <span className="text-2xl">{template.emoji}</span>
                        </div>
                        <div>
                          <h3 className="font-bold text-foreground">{template.name}</h3>
                          <p className="text-sm text-foreground-secondary">{template.desc}</p>
                        </div>
                      </div>
                      <Switch defaultChecked />
                    </div>
                  </div>

                  {/* 结构 */}
                  <div className="p-4 space-y-3">
                    <h4 className="text-sm font-medium text-foreground">脚本结构</h4>
                    <div className="space-y-2">
                      {template.structure.map((step, idx) => (
                        <div key={idx} className="flex items-start gap-3 p-2 rounded-lg bg-background-tertiary">
                          <div className={`w-6 h-6 rounded-full bg-gradient-to-br ${template.color} flex items-center justify-center flex-shrink-0`}>
                            <span className="text-xs text-white font-bold">{idx + 1}</span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm text-foreground">{step.part}</span>
                              <Badge variant="default" size="sm">{step.duration}</Badge>
                            </div>
                            <p className="text-xs text-foreground-secondary mt-0.5">{step.desc}</p>
                            <p className="text-xs text-foreground-tertiary mt-1 truncate">{step.example}</p>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* 特色 */}
                    <div className="pt-3 border-t border-border">
                      {template.keywords && (
                        <div className="mb-2">
                          <span className="text-xs text-foreground-tertiary">关键词: </span>
                          {template.keywords.map((kw, i) => (
                            <span key={i} className="text-xs text-foreground-secondary mr-2">&ldquo;{kw}&rdquo;</span>
                          ))}
                        </div>
                      )}
                      {template.hookTechniques && (
                        <div className="mb-2">
                          <span className="text-xs text-foreground-tertiary">勾子技巧: </span>
                          {template.hookTechniques.map((ht, i) => (
                            <Badge key={i} variant="default" size="sm" className="mr-1">{ht}</Badge>
                          ))}
                        </div>
                      )}
                      {template.topicMethods && (
                        <div className="mb-2">
                          <span className="text-xs text-foreground-tertiary">选题法: </span>
                          {template.topicMethods.map((tm, i) => (
                            <span key={i} className="text-xs text-foreground-secondary mr-2">{tm}</span>
                          ))}
                        </div>
                      )}
                      {template.prototypes && (
                        <div className="mb-2">
                          <span className="text-xs text-foreground-tertiary">故事原型: </span>
                          {template.prototypes.map((p, i) => (
                            <span key={i} className="text-xs text-foreground-secondary mr-2">{p}</span>
                          ))}
                        </div>
                      )}
                      <p className="text-xs text-accent-green mt-2">
                        <TrendingUp className="w-3 h-3 inline mr-1" />
                        最适合：{template.bestFor}
                      </p>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="deconstruct">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader 
                title="输入竞品链接" 
                description="粘贴抖音/视频号/小红书链接"
              />
              <div className="space-y-4">
                <Input
                  placeholder="https://v.douyin.com/xxxxx"
                  leftIcon={<LinkIcon className="w-4 h-4" />}
                />
                <Button className="w-full" leftIcon={<Scissors className="w-4 h-4" />}>
                  开始解构
                </Button>
              </div>
            </Card>

            <Card>
              <CardHeader title="解构结果" description="分析视频结构和关键要素" />
              <div className="space-y-3">
                {[
                  { part: '黄金3秒', content: '钩子：90%的人不知道...', type: 'hook' },
                  { part: '脚本模板识别', content: '检测为「说观点」模板', type: 'template', template: 'opinion' },
                  { part: '情绪铺垫', content: '讲述失败经历，建立共鸣', type: 'setup' },
                  { part: '冲突转折', content: '但是我发现了一个秘密...', type: 'conflict' },
                  { part: '高潮论证', content: '用数据和案例支撑观点', type: 'climax' },
                  { part: '结尾CTA', content: '关注我看更多干货', type: 'cta' },
                ].map((item, index) => (
                  <div key={index} className="p-3 rounded-xl bg-background-tertiary">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant={item.type === 'template' ? 'success' : 'primary'} size="sm">{item.part}</Badge>
                      {item.template && (
                        <span className="text-xs text-accent-green">💡 说观点模板</span>
                      )}
                    </div>
                    <p className="text-sm text-foreground-secondary">{item.content}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="remix">
          <Card>
            <CardHeader 
              title="重组版本生成" 
              description="基于解构结果和四大模板生成3个IP化版本"
            />
            <div className="space-y-4">
              {[
                { emotion: '愤怒版', desc: '直击痛点，引发共鸣', color: 'from-red-500 to-orange-500', template: 'opinion' },
                { emotion: '希望版', desc: '积极向上，传递力量', color: 'from-green-500 to-teal-500', template: 'story' },
                { emotion: '好奇版', desc: '悬念设置，引导思考', color: 'from-blue-500 to-purple-500', template: 'knowledge' },
              ].map((version, index) => (
                <div key={index} className="p-4 rounded-xl bg-background-tertiary border border-border">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${version.color} flex items-center justify-center`}>
                        <span className="text-white font-bold">{index + 1}</span>
                      </div>
                      <div>
                        <h4 className="font-medium text-foreground">{version.emotion}</h4>
                        <p className="text-xs text-foreground-tertiary">{version.desc}</p>
                      </div>
                      <Badge variant="primary" size="sm">
                        {SCRIPT_TEMPLATES.find(t => t.id === version.template)?.name}
                      </Badge>
                    </div>
                    <Button size="sm" leftIcon={<Play className="w-4 h-4" />}>
                      生成
                    </Button>
                  </div>
                  <div className="p-3 rounded-lg bg-background-elevated">
                    <p className="text-sm text-foreground-secondary">
                      [生成的文案内容将显示在这里...]
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="rules">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader title="解构规则" description="提取竞品的哪些要素" />
              <div className="space-y-3">
                {[
                  { name: '脚本模板识别', desc: '自动识别使用的四大模板类型', enabled: true },
                  { name: '钩子模式', desc: '分析开头如何吸引注意力', enabled: true },
                  { name: '情绪曲线', desc: '识别情绪起伏的时间点', enabled: true },
                  { name: '论证结构', desc: '提取逻辑框架和论据类型', enabled: true },
                  { name: '视觉元素', desc: '分析画面切换和特效使用', enabled: false },
                ].map((rule) => (
                  <label key={rule.name} className="flex items-start gap-3 p-3 rounded-xl bg-background-tertiary cursor-pointer">
                    <input type="checkbox" defaultChecked={rule.enabled} className="mt-1" />
                    <div>
                      <p className="font-medium text-foreground">{rule.name}</p>
                      <p className="text-xs text-foreground-tertiary">{rule.desc}</p>
                    </div>
                  </label>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader title="原创度保障" description="防止内容过于相似" />
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-foreground">文本重复率阈值</span>
                    <span className="text-sm font-medium text-foreground">25%</span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="50"
                    defaultValue="25"
                    className="w-full h-2 bg-background-elevated rounded-lg appearance-none cursor-pointer accent-primary-500"
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-foreground">结构相似度阈值</span>
                    <span className="text-sm font-medium text-foreground">40%</span>
                  </div>
                  <input
                    type="range"
                    min="20"
                    max="60"
                    defaultValue="40"
                    className="w-full h-2 bg-background-elevated rounded-lg appearance-none cursor-pointer accent-primary-500"
                  />
                </div>
                <div className="p-3 rounded-lg bg-accent-green/10 border border-accent-green/20">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-accent-green" />
                    <span className="text-sm text-accent-green">当前设置符合平台安全标准</span>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="config">
          <Card>
            <CardHeader title="高级配置" description="重组策略参数" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Select
                label="脚本模板偏好"
                options={[
                  { value: 'auto', label: '自动识别（推荐）' },
                  { value: 'opinion', label: '优先使用「说观点」' },
                  { value: 'process', label: '优先使用「晒过程」' },
                  { value: 'knowledge', label: '优先使用「教知识」' },
                  { value: 'story', label: '优先使用「讲故事」' },
                ]}
              />
              <Select
                label="杂交策略"
                options={[
                  { value: 'best_of_breed', label: 'Best of Breed（每个节点取最优）' },
                  { value: 'single', label: '单一竞品深度解构' },
                  { value: 'hybrid', label: '多竞品融合' },
                ]}
              />
              <Select
                label="强制替换规则"
                options={[
                  { value: 'all', label: '竞品案例100%替换' },
                  { value: 'partial', label: '部分替换' },
                  { value: 'none', label: '不强制替换' },
                ]}
              />
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </MainLayout>
  );
}

// Switch组件（简化版）
function Switch({ defaultChecked, size = 'md' }: { defaultChecked?: boolean; size?: 'sm' | 'md' }) {
  const sizeClasses = size === 'sm' ? 'w-8 h-4' : 'w-11 h-6';
  const dotSize = size === 'sm' ? 'w-3 h-3' : 'w-5 h-5';
  const translate = defaultChecked ? 'translate-x-full' : 'translate-x-0.5';
  const bg = defaultChecked ? 'bg-primary-500' : 'bg-background-elevated';
  
  return (
    <div className={`${sizeClasses} ${bg} rounded-full relative transition-colors cursor-pointer`}>
      <div className={`absolute top-0.5 ${translate} ${dotSize} bg-white rounded-full transition-transform`} />
    </div>
  );
}
