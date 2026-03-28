'use client';

import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Input';
import { 
  Shield, 
  AlertTriangle, 
  CheckCircle2, 
  Plus,
  Trash2,
  FileText
} from 'lucide-react';

export default function ComplianceAgentPage() {
  return (
    <MainLayout title="合规Agent - 配置">
      {/* Agent header */}
      <div className="mb-6 p-6 rounded-2xl bg-gradient-to-r from-emerald-500/10 to-teal-600/10 border border-emerald-500/20">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-2xl">
            🛡️
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-foreground">合规Agent</h2>
            <p className="text-foreground-secondary">工业刹车系统，三级审查内容合规性</p>
          </div>
          <Badge variant="success" dot>运行中</Badge>
        </div>
      </div>

      <Tabs defaultValue="review" className="w-full">
        <TabsList>
          <TabsTrigger value="review">内容审查</TabsTrigger>
          <TabsTrigger value="keywords">敏感词库</TabsTrigger>
          <TabsTrigger value="platforms">平台规则</TabsTrigger>
          <TabsTrigger value="config">审核配置</TabsTrigger>
        </TabsList>

        <TabsContent value="review">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader title="输入待审查内容" description="粘贴文案进行合规检查" />
              <div className="space-y-4">
                <Textarea
                  placeholder="粘贴需要审查的文案内容..."
                  className="min-h-[240px]"
                />
                <Button className="w-full" leftIcon={<Shield className="w-4 h-4" />}>
                  开始审查
                </Button>
              </div>
            </Card>

            <Card>
              <CardHeader title="审查结果" description="三级审查结果展示" />
              <div className="space-y-4">
                {/* 平台合规 */}
                <div className="p-4 rounded-xl bg-accent-green/10 border border-accent-green/20">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle2 className="w-5 h-5 text-accent-green" />
                    <span className="font-medium text-accent-green">平台合规检查</span>
                  </div>
                  <p className="text-sm text-foreground-secondary">未发现敏感词或导流违规</p>
                </div>

                {/* 广告法合规 */}
                <div className="p-4 rounded-xl bg-accent-yellow/10 border border-accent-yellow/20">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="w-5 h-5 text-accent-yellow" />
                    <span className="font-medium text-accent-yellow">广告法合规检查</span>
                  </div>
                  <p className="text-sm text-foreground-secondary">发现1处疑似违规</p>
                  <div className="mt-2 p-2 rounded bg-background-elevated">
                    <p className="text-sm">
                      <span className="text-accent-red line-through">最好</span>
                      {' → '}
                      <span className="text-accent-green">非常不错</span>
                    </p>
                  </div>
                </div>

                {/* 原创合规 */}
                <div className="p-4 rounded-xl bg-accent-green/10 border border-accent-green/20">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle2 className="w-5 h-5 text-accent-green" />
                    <span className="font-medium text-accent-green">原创合规检查</span>
                  </div>
                  <p className="text-sm text-foreground-secondary">查重率 12%，低于 25% 阈值</p>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="keywords">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card>
              <CardHeader 
                title="🔴 红线词汇" 
                description="严格阻断，无法发布"
                action={<Button size="sm" leftIcon={<Plus className="w-4 h-4" />}>添加</Button>}
              />
              <div className="space-y-2">
                {['政治敏感', '色情低俗', '暴力恐怖', '诈骗'].map((word) => (
                  <div key={word} className="flex items-center justify-between p-2 rounded-lg bg-accent-red/10">
                    <span className="text-sm text-accent-red">{word}</span>
                    <Button variant="ghost" size="sm" leftIcon={<Trash2 className="w-3 h-3" />} />
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader 
                title="🟡 黄线词汇" 
                description="警告提示，需人工确认"
                action={<Button size="sm" leftIcon={<Plus className="w-4 h-4" />}>添加</Button>}
              />
              <div className="space-y-2">
                {['最佳', '第一', '国家级', '独家'].map((word) => (
                  <div key={word} className="flex items-center justify-between p-2 rounded-lg bg-accent-yellow/10">
                    <span className="text-sm text-accent-yellow">{word}</span>
                    <Button variant="ghost" size="sm" leftIcon={<Trash2 className="w-3 h-3" />} />
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader 
                title="🔵 建议替换" 
                description="自动提供替换建议"
                action={<Button size="sm" leftIcon={<Plus className="w-4 h-4" />}>添加</Button>}
              />
              <div className="space-y-2">
                {[
                  { word: '最好', replace: '非常不错' },
                  { word: '最便宜', replace: '性价比很高' },
                  { word: '绝对', replace: '非常' },
                ].map((item) => (
                  <div key={item.word} className="flex items-center justify-between p-2 rounded-lg bg-accent-cyan/10">
                    <span className="text-sm text-accent-cyan">{item.word}</span>
                    <span className="text-xs text-foreground-muted">→ {item.replace}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="platforms">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              { name: '抖音', rules: ['禁止站外引流', '禁说微信', '禁用极限词'], icon: '🎵' },
              { name: '视频号', rules: ['禁过度营销', '禁医疗绝对词', '禁金融诱导'], icon: '📺' },
              { name: '小红书', rules: ['禁站外导流', '禁最低价', '禁虚假宣传'], icon: '📕' },
              { name: '快手', rules: ['禁低俗内容', '禁恶意炒作', '禁虚假承诺'], icon: '⚡' },
            ].map((platform) => (
              <Card key={platform.name}>
                <CardHeader title={`${platform.icon} ${platform.name}`} />
                <div className="space-y-2">
                  {platform.rules?.map((rule, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-accent-red" />
                      <span className="text-sm text-foreground-secondary">{rule}</span>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="config">
          <Card>
            <CardHeader title="审核配置" description="全局审核策略" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Select
                label="审核严格度"
                options={[
                  { value: 'strict', label: '严格模式（宁可错杀）' },
                  { value: 'normal', label: '标准模式（平衡）' },
                  { value: 'loose', label: '宽松模式（宁可放过）' },
                ]}
              />
              <Select
                label="自动修正"
                options={[
                  { value: 'auto', label: '自动替换违规词' },
                  { value: 'suggest', label: '仅提供修改建议' },
                  { value: 'none', label: '不自动修改' },
                ]}
              />
              <label className="flex items-center gap-3 cursor-pointer">
                <div className="relative">
                  <input type="checkbox" className="sr-only peer" defaultChecked />
                  <div className="w-11 h-6 rounded-full bg-background-elevated peer-checked:bg-primary-500 transition-colors" />
                  <div className="absolute left-1 top-1 w-4 h-4 rounded-full bg-white transition-transform peer-checked:translate-x-5" />
                </div>
                <div>
                  <span className="text-sm font-medium text-foreground">医疗/金融强监管</span>
                  <p className="text-xs text-foreground-tertiary">此类内容需额外资质检查</p>
                </div>
              </label>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </MainLayout>
  );
}
