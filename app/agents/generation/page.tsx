'use client';

import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { 
  FileText, 
  Sparkles, 
  Settings,
  Plus,
  Trash2,
  Wand2,
  Heart,
  Zap,
  TrendingUp,
  TrendingDown,
  Activity,
  Flame,
  AlertCircle,
  CheckCircle2,
  Brain
} from 'lucide-react';

// 情感曲线模板（工业化爆款生产流水线核心方法论）
const EMOTION_CURVES = [
  {
    id: 'angerHope',
    name: '愤怒-希望型',
    emoji: '🔥→✨',
    desc: '解决方案类',
    curve: [
      { phase: '痛点激怒', percentage: 20, emotion: '愤怒', color: 'bg-red-500', desc: '直击痛点，引发共鸣' },
      { phase: '情绪共鸣', percentage: 30, emotion: '共情', color: 'bg-orange-500', desc: '建立情感连接' },
      { phase: '解决方案', percentage: 40, emotion: '希望', color: 'bg-green-500', desc: '提供可行方案' },
      { phase: '行动号召', percentage: 10, emotion: '激励', color: 'bg-blue-500', desc: '引导下一步行动' },
    ],
    bestFor: '痛点类、解决方案类内容',
    example: '"90%的人都在犯的错...我也是受害者...但这个方法救了我...现在分享给你"'
  },
  {
    id: 'curiosityShock',
    name: '好奇-震惊型',
    emoji: '🤔→😱',
    desc: '揭秘类',
    curve: [
      { phase: '悬念设置', percentage: 25, emotion: '好奇', color: 'bg-purple-500', desc: '抛出悬念问题' },
      { phase: '逐步揭秘', percentage: 35, emotion: '期待', color: 'bg-indigo-500', desc: '层层剥开真相' },
      { phase: '震惊事实', percentage: 30, emotion: '震惊', color: 'bg-pink-500', desc: '揭示惊人真相' },
      { phase: '引导互动', percentage: 10, emotion: '思考', color: 'bg-cyan-500', desc: '引发观众思考' },
    ],
    bestFor: '行业内幕、揭秘类内容',
    example: '"你知道为什么...其实真相是...更可怕的是...你是怎么看的？"'
  },
  {
    id: 'problemSolution',
    name: '问题-解决型',
    emoji: '❓→✅',
    desc: '干货教程类',
    curve: [
      { phase: '问题呈现', percentage: 20, emotion: '困惑', color: 'bg-yellow-500', desc: '展示具体问题' },
      { phase: '原因分析', percentage: 30, emotion: '理解', color: 'bg-amber-500', desc: '解释产生原因' },
      { phase: '解决步骤', percentage: 40, emotion: '希望', color: 'bg-green-500', desc: '详细解决步骤' },
      { phase: '总结强调', percentage: 10, emotion: '确信', color: 'bg-blue-500', desc: '强调核心价值' },
    ],
    bestFor: '教程类、干货类内容',
    example: '"总是遇到...问题？原因是...解决方法如下...记住这一点就够了"'
  },
  {
    id: 'empathyInspire',
    name: '共情-励志型',
    emoji: '💔→💪',
    desc: '个人故事类',
    curve: [
      { phase: '困境共情', percentage: 25, emotion: '共鸣', color: 'bg-red-400', desc: '分享困难经历' },
      { phase: '转折希望', percentage: 25, emotion: '希望', color: 'bg-orange-400', desc: '转折点出现' },
      { phase: '方法价值', percentage: 35, emotion: '启发', color: 'bg-green-500', desc: '分享成功经验' },
      { phase: '结果证明', percentage: 15, emotion: '激励', color: 'bg-blue-500', desc: '展示成果' },
    ],
    bestFor: '个人成长、励志类内容',
    example: '"那时候我...直到...后来我发现...现在我已经...你也可以"'
  },
];

export default function GenerationAgentPage() {
  return (
    <MainLayout title="生成Agent - 配置">
      {/* Agent header */}
      <div className="mb-6 p-6 rounded-2xl bg-gradient-to-r from-amber-500/10 to-orange-600/10 border border-amber-500/20">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-2xl">
            ✍️
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-foreground">生成Agent</h2>
            <p className="text-foreground-secondary">转化为符合IP风格的终稿文案，情感曲线智能设计</p>
          </div>
          <Badge variant="warning" dot>配置中</Badge>
        </div>
      </div>

      <Tabs defaultValue="emotion" className="w-full">
        <TabsList>
          <TabsTrigger value="emotion">情感曲线</TabsTrigger>
          <TabsTrigger value="style">风格训练</TabsTrigger>
          <TabsTrigger value="language">语言指纹</TabsTrigger>
          <TabsTrigger value="generate">文案生成</TabsTrigger>
          <TabsTrigger value="config">高级配置</TabsTrigger>
        </TabsList>

        {/* 情感曲线配置 */}
        <TabsContent value="emotion">
          <div className="space-y-6">
            {/* 说明 */}
            <div className="p-4 bg-gradient-to-r from-rose-500/10 to-pink-500/10 rounded-xl border border-rose-500/20">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-rose-500 to-pink-500 flex items-center justify-center">
                  <Activity className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-medium text-foreground mb-1">情感曲线设计</h3>
                  <p className="text-sm text-foreground-secondary">
                    爆款内容的情绪是有<span className="text-rose-400">节奏和曲线</span>的。
                    AI会根据你选择的模板类型，自动设计最适合的情感曲线，让观众跟着你的节奏走。
                  </p>
                </div>
              </div>
            </div>

            {/* 情感曲线卡片 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {EMOTION_CURVES.map((curve) => (
                <Card key={curve.id} className="overflow-hidden">
                  {/* 头部 */}
                  <div className="p-4 bg-gradient-to-r from-rose-500/10 to-pink-500/10 border-b border-rose-500/20">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-3xl">{curve.emoji}</span>
                        <div>
                          <h3 className="font-bold text-foreground">{curve.name}</h3>
                          <p className="text-sm text-foreground-secondary">{curve.desc}</p>
                        </div>
                      </div>
                      <Switch defaultChecked={curve.id === 'angerHope'} />
                    </div>
                  </div>

                  {/* 情感曲线可视化 */}
                  <div className="p-4">
                    <h4 className="text-sm font-medium text-foreground mb-4">情感曲线</h4>
                    
                    {/* 曲线图表 */}
                    <div className="relative h-24 mb-4 bg-background-tertiary rounded-lg overflow-hidden">
                      <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
                        <defs>
                          <linearGradient id={`gradient-${curve.id}`} x1="0%" y1="0%" x2="100%" y2="0%">
                            {curve.curve.map((point, i) => (
                              <stop 
                                key={i} 
                                offset={`${i * (100 / (curve.curve.length - 1))}%`} 
                                className={point.color.replace('bg-', 'text-')}
                                stopColor="currentColor"
                              />
                            ))}
                          </linearGradient>
                        </defs>
                        <path
                          d={`M 0,${100 - curve.curve[0].percentage} ${curve.curve.map((p, i) => {
                            const x = (i / (curve.curve.length - 1)) * 100;
                            const y = 100 - p.percentage;
                            return `L ${x},${y}`;
                          }).join(' ')}`}
                          fill="none"
                          stroke={`url(#gradient-${curve.id})`}
                          strokeWidth="3"
                          className="opacity-80"
                        />
                      </svg>
                      
                      {/* 节点标记 */}
                      {curve.curve.map((point, i) => (
                        <div
                          key={i}
                          className="absolute top-1/2 -translate-y-1/2 flex flex-col items-center"
                          style={{ left: `${(i / (curve.curve.length - 1)) * 100}%`, transform: 'translateX(-50%) translateY(-50%)' }}
                        >
                          <div className={`w-3 h-3 rounded-full ${point.color} border-2 border-white shadow-lg`} />
                        </div>
                      ))}
                    </div>

                    {/* 阶段详情 */}
                    <div className="space-y-2">
                      {curve.curve.map((point, idx) => (
                        <div key={idx} className="flex items-center gap-3 p-2 rounded-lg bg-background-tertiary">
                          <div className={`w-2 h-8 rounded-full ${point.color}`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between">
                              <span className="font-medium text-sm text-foreground">{point.phase}</span>
                              <div className="flex items-center gap-2">
                                <Badge variant="default" size="sm">{point.percentage}%</Badge>
                                <span className={`text-xs px-2 py-0.5 rounded-full ${point.color} bg-opacity-20 text-white`}>
                                  {point.emotion}
                                </span>
                              </div>
                            </div>
                            <p className="text-xs text-foreground-tertiary mt-0.5">{point.desc}</p>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* 适用场景 */}
                    <div className="mt-4 pt-3 border-t border-border">
                      <p className="text-xs text-foreground-tertiary mb-1">最适合：</p>
                      <p className="text-sm text-accent-green">{curve.bestFor}</p>
                    </div>

                    {/* 示例 */}
                    <div className="mt-3 p-2 bg-background-elevated rounded-lg">
                      <p className="text-xs text-foreground-tertiary">示例文案结构：</p>
                      <p className="text-sm text-foreground-secondary mt-1 italic">{curve.example}</p>
                    </div>
                  </div>
                </Card>
              ))}
            </div>

            {/* 自动匹配配置 */}
            <Card>
              <CardHeader 
                title="情感曲线自动匹配" 
                description="根据脚本模板自动选择最佳情感曲线"
              />
              <div className="space-y-3">
                {[
                  { template: '说观点', curve: '愤怒-希望型', reason: '观点类内容需要引发共鸣' },
                  { template: '晒过程', curve: '好奇-震惊型', reason: '过程展示需要保持悬念' },
                  { template: '教知识', curve: '问题-解决型', reason: '知识类内容逻辑性强' },
                  { template: '讲故事', curve: '共情-励志型', reason: '故事需要情感起伏' },
                ].map((mapping, index) => (
                  <div key={index} className="flex items-center justify-between p-3 rounded-xl bg-background-tertiary">
                    <div className="flex items-center gap-3">
                      <Badge variant="primary" size="sm">{mapping.template}</Badge>
                      <span className="text-foreground-secondary">→</span>
                      <Badge variant="success" size="sm">{mapping.curve}</Badge>
                    </div>
                    <span className="text-xs text-foreground-tertiary">{mapping.reason}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="style">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader 
                title="风格训练集" 
                description="上传50条S级文案训练专属模型"
              />
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-background-tertiary border border-dashed border-border">
                  <div className="text-center">
                    <FileText className="w-8 h-8 mx-auto mb-2 text-foreground-tertiary" />
                    <p className="text-sm text-foreground-secondary">拖拽文件到此处或点击上传</p>
                    <p className="text-xs text-foreground-muted mt-1">支持 .txt, .docx, .pdf</p>
                    <Button variant="secondary" size="sm" className="mt-3">
                      选择文件
                    </Button>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-foreground-secondary">已上传文案</span>
                  <Badge variant="primary" size="sm">32 / 50</Badge>
                </div>
                <div className="w-full h-2 bg-background-elevated rounded-full overflow-hidden">
                  <div className="h-full bg-primary-500 rounded-full" style={{ width: '64%' }} />
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader title="风格强度" description="调节AI模仿IP风格的程度" />
              <div className="space-y-6">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-foreground">风格强度</span>
                    <span className="text-sm font-medium text-foreground">80%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    defaultValue="80"
                    className="w-full h-2 bg-background-elevated rounded-lg appearance-none cursor-pointer accent-primary-500"
                  />
                  <p className="text-xs text-foreground-tertiary mt-2">
                    推荐80%：既像IP又有新意
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-background-tertiary">
                  <p className="text-sm font-medium text-foreground mb-2">训练状态</p>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
                    <span className="text-sm text-foreground-secondary">训练中... 预计还需 15 分钟</span>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="language">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader 
                title="口头禅管理" 
                description="IP标志性短语"
                action={<Button size="sm" leftIcon={<Plus className="w-4 h-4" />}>添加</Button>}
              />
              <div className="space-y-3">
                {[
                  { phrase: '你知道吗', frequency: '高频' },
                  { phrase: '我跟你讲', frequency: '中频' },
                  { phrase: '说实话', frequency: '低频' },
                ].map((item, index) => (
                  <div key={index} className="flex items-center justify-between p-3 rounded-xl bg-background-tertiary">
                    <div className="flex items-center gap-3">
                      <span className="text-foreground">&ldquo;{item.phrase}&rdquo;</span>
                      <Badge variant="default" size="sm">{item.frequency}</Badge>
                    </div>
                    <Button variant="ghost" size="sm" leftIcon={<Trash2 className="w-4 h-4" />} />
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader 
                title="禁忌词汇" 
                description="绝对不用"
                action={<Button size="sm" leftIcon={<Plus className="w-4 h-4" />}>添加</Button>}
              />
              <div className="space-y-3">
                {['亲们', '宝宝们', '显然', '必须'].map((word) => (
                  <div key={word} className="flex items-center justify-between p-3 rounded-xl bg-background-tertiary">
                    <span className="text-foreground">{word}</span>
                    <span className="text-xs text-foreground-tertiary">太微商/太说教</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader title="句长偏好" description="长短句比例" />
              <div className="space-y-3">
                {[
                  { type: '短句（<15字）', value: 60 },
                  { type: '中句（15-30字）', value: 30 },
                  { type: '长句（>30字）', value: 10 },
                ].map((item) => (
                  <div key={item.type}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-foreground">{item.type}</span>
                      <span className="text-sm font-medium text-foreground">{item.value}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-background-elevated rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-primary-500 rounded-full" 
                        style={{ width: `${item.value}%` }} 
                      />
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader title="修辞偏好" description="喜欢的表达手法" />
              <div className="flex flex-wrap gap-2">
                {['极端数字（90%/100万）', '身体隐喻', '反问句', '排比', '对比'].map((item) => (
                  <span key={item} className="px-3 py-1.5 rounded-lg bg-background-tertiary text-sm text-foreground">
                    {item}
                  </span>
                ))}
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="generate">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader title="输入主题" description="输入想要生成的内容主题" />
              <div className="space-y-4">
                <Textarea
                  placeholder="例如：创业者如何度过低谷期..."
                  className="min-h-[150px]"
                />
                
                {/* 快速选择情感曲线 */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">情感曲线</label>
                  <div className="grid grid-cols-2 gap-2">
                    {EMOTION_CURVES.map((curve) => (
                      <button
                        key={curve.id}
                        className="flex items-center gap-2 p-2 rounded-lg border border-border bg-background-tertiary hover:border-primary-500/50 transition-all text-left"
                      >
                        <span className="text-lg">{curve.emoji}</span>
                        <div>
                          <div className="text-sm font-medium text-foreground">{curve.name}</div>
                          <div className="text-xs text-foreground-tertiary">{curve.desc}</div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <Button className="w-full" leftIcon={<Wand2 className="w-4 h-4" />}>
                  生成文案
                </Button>
              </div>
            </Card>

            <Card>
              <CardHeader title="生成结果" description="AI生成的文案草稿" />
              <div className="p-4 rounded-xl bg-background-tertiary min-h-[200px]">
                <p className="text-sm text-foreground-secondary">
                  [生成的文案将显示在这里...]
                </p>
              </div>
              <div className="flex gap-2 mt-4">
                <Button variant="secondary" size="sm" className="flex-1">
                  复制
                </Button>
                <Button variant="secondary" size="sm" className="flex-1">
                  重新生成
                </Button>
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="config">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader title="情感曲线强度" description="调节情感起伏幅度" />
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-foreground">情绪起伏强度</span>
                    <span className="text-sm font-medium text-foreground">70%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    defaultValue="70"
                    className="w-full h-2 bg-background-elevated rounded-lg appearance-none cursor-pointer accent-primary-500"
                  />
                  <p className="text-xs text-foreground-tertiary mt-2">
                    推荐70%：有明显情感变化但不夸张
                  </p>
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader title="去AI化" description="增加真实感" />
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-foreground">口语瑕疵频率</span>
                    <span className="text-sm font-medium text-foreground">2处/100字</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="5"
                    defaultValue="2"
                    className="w-full h-2 bg-background-elevated rounded-lg appearance-none cursor-pointer accent-primary-500"
                  />
                </div>
                <p className="text-xs text-foreground-tertiary">
                  自动插入&ldquo;呃&rdquo;&ldquo;那个&rdquo;等口语词，打破对仗工整
                </p>
              </div>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </MainLayout>
  );
}

// Switch组件（简化版）
function Switch({ defaultChecked }: { defaultChecked?: boolean }) {
  return (
    <div className={`w-11 h-6 ${defaultChecked ? 'bg-primary-500' : 'bg-background-elevated'} rounded-full relative transition-colors cursor-pointer`}>
      <div className={`absolute top-0.5 ${defaultChecked ? 'translate-x-full' : 'translate-x-0.5'} w-5 h-5 bg-white rounded-full transition-transform`} style={{ transform: defaultChecked ? 'translateX(20px)' : 'translateX(2px)' }} />
    </div>
  );
}
