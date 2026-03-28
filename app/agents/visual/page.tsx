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
  Video, 
  Camera, 
  Music, 
  Image as ImageIcon,
  Play,
  Settings
} from 'lucide-react';

export default function VisualAgentPage() {
  return (
    <MainLayout title="视觉Agent - 配置">
      {/* Agent header */}
      <div className="mb-6 p-6 rounded-2xl bg-gradient-to-r from-blue-500/10 to-indigo-600/10 border border-blue-500/20">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-2xl">
            🎬
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-foreground">视觉Agent</h2>
            <p className="text-foreground-secondary">文案转视觉方案，数字人自动拍摄</p>
          </div>
          <Badge variant="success" dot>运行中</Badge>
        </div>
      </div>

      <Tabs defaultValue="digital" className="w-full">
        <TabsList>
          <TabsTrigger value="digital">数字人</TabsTrigger>
          <TabsTrigger value="storyboard">分镜脚本</TabsTrigger>
          <TabsTrigger value="scenes">场景库</TabsTrigger>
          <TabsTrigger value="config">高级配置</TabsTrigger>
        </TabsList>

        <TabsContent value="digital">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader title="数字人形象" description="HeyGen 数字人配置" />
              <div className="space-y-4">
                <div className="aspect-video rounded-xl bg-background-tertiary flex items-center justify-center">
                  <div className="text-center">
                    <Camera className="w-12 h-12 mx-auto mb-2 text-foreground-tertiary" />
                    <p className="text-sm text-foreground-secondary">数字人预览</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="secondary" className="flex-1">上传训练视频</Button>
                  <Button variant="secondary" className="flex-1">克隆声音</Button>
                </div>
                <p className="text-xs text-foreground-muted">
                  需要3分钟正面半身视频，生成专属数字人
                </p>
              </div>
            </Card>

            <Card>
              <CardHeader title="生成视频" description="输入文案自动生成数字人视频" />
              <div className="space-y-4">
                <Textarea
                  placeholder="输入口播文案..."
                  className="min-h-[150px]"
                />
                <Select
                  label="语速"
                  options={[
                    { value: '0.8', label: '慢速' },
                    { value: '1.0', label: '正常' },
                    { value: '1.2', label: '快速' },
                  ]}
                />
                <Button className="w-full" leftIcon={<Play className="w-4 h-4" />}>
                  生成视频
                </Button>
                <div className="p-3 rounded-lg bg-background-tertiary">
                  <p className="text-xs text-foreground-secondary">
                    💡 B级内容：约2小时出片，成本 $2/条
                  </p>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="storyboard">
          <Card>
            <CardHeader title="智能分镜脚本" description="根据文案情绪自动生成景别和运镜" />
            <div className="space-y-4">
              <Textarea
                placeholder="输入文案内容..."
                className="min-h-[100px]"
              />
              <Button className="w-full">生成分镜</Button>
              
              <div className="space-y-3">
                {[
                  { time: '0-3s', content: '钩子：你知道吗', shot: '特写', emotion: '好奇' },
                  { time: '3-15s', content: '讲述背景故事', shot: '中景', emotion: '共情' },
                  { time: '15-30s', content: '提出解决方案', shot: '近景', emotion: '希望' },
                  { time: '30-45s', content: '行动号召', shot: '特写', emotion: '紧迫' },
                ].map((scene, index) => (
                  <div key={index} className="flex gap-4 p-4 rounded-xl bg-background-tertiary">
                    <div className="w-16 text-sm font-mono text-foreground-muted">{scene.time}</div>
                    <div className="flex-1">
                      <p className="text-sm text-foreground">{scene.content}</p>
                      <div className="flex gap-2 mt-2">
                        <Badge variant="primary" size="sm">{scene.shot}</Badge>
                        <Badge variant="default" size="sm">{scene.emotion}</Badge>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="scenes">
          <Card>
            <CardHeader title="场景库" description="常用拍摄场地管理" />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                { name: '办公室', type: '室内', light: '自然光' },
                { name: '咖啡厅', type: '室内', light: '暖光' },
                { name: '夜景窗边', type: '室内', light: '氛围光' },
                { name: '户外天台', type: '室外', light: '自然光' },
                { name: '会议室', type: '室内', light: '顶光' },
                { name: '书房', type: '室内', light: '台灯' },
              ].map((scene) => (
                <div key={scene.name} className="p-4 rounded-xl bg-background-tertiary">
                  <div className="aspect-video rounded-lg bg-background-elevated mb-3 flex items-center justify-center">
                    <ImageIcon className="w-8 h-8 text-foreground-tertiary" />
                  </div>
                  <h4 className="font-medium text-foreground">{scene.name}</h4>
                  <div className="flex gap-2 mt-1">
                    <span className="text-xs text-foreground-tertiary">{scene.type}</span>
                    <span className="text-xs text-foreground-tertiary">·</span>
                    <span className="text-xs text-foreground-tertiary">{scene.light}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="config">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader title="BGM库" description="情绪音乐分类" />
              <div className="space-y-3">
                {['紧张', '愤怒', '希望', '爽感', '温暖'].map((emotion) => (
                  <div key={emotion} className="flex items-center justify-between p-3 rounded-xl bg-background-tertiary">
                    <div className="flex items-center gap-3">
                      <Music className="w-5 h-5 text-foreground-tertiary" />
                      <span className="text-foreground">{emotion}</span>
                    </div>
                    <Badge variant="default" size="sm">3首</Badge>
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader title="景别配比" description="A级/B级差异" />
              <div className="space-y-4">
                <div>
                  <p className="text-sm font-medium text-foreground mb-2">A级内容（人设型）</p>
                  <div className="flex gap-2">
                    <Badge variant="primary" size="sm">特写 40%</Badge>
                    <Badge variant="primary" size="sm">中景 40%</Badge>
                    <Badge variant="primary" size="sm">全景 20%</Badge>
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground mb-2">B级内容（流量型）</p>
                  <div className="flex gap-2">
                    <Badge variant="secondary" size="sm">特写 20%</Badge>
                    <Badge variant="secondary" size="sm">中景 60%</Badge>
                    <Badge variant="secondary" size="sm">全景 20%</Badge>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </MainLayout>
  );
}
