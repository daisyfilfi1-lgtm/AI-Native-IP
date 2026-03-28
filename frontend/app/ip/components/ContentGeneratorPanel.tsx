'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { 
  Loader2, 
  Flame, 
  Copy, 
  Check,
  TrendingUp,
  PenLine,
  Zap
} from 'lucide-react';
import { api } from '@/lib/api';

// ==================== 类型定义 ====================

interface ContentResult {
  content: string;
  score: number;
  scenario: string;
  metadata: Record<string, any>;
}

interface FourDimWeights {
  relevance: number;
  hotness: number;
  competition: number;
  conversion: number;
}

// ==================== 场景一：热点选题 ====================

export function ScenarioOnePanel({ ipId }: { ipId: string }) {
  const [platform, setPlatform] = useState('all');
  const [weights, setWeights] = useState<FourDimWeights>({
    relevance: 0.3,
    hotness: 0.3,
    competition: 0.2,
    conversion: 0.2,
  });
  const [count, setCount] = useState(5);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ContentResult[]>([]);
  const [copied, setCopied] = useState<string | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setResults([]);
    try {
      const data = await api.content.scenarioOne(ipId, platform, weights, count);
      setResults(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const copyContent = async (content: string, idx: number) => {
    await navigator.clipboard.writeText(content);
    setCopied(idx.toString());
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="space-y-4">
      {/* 配置区域 */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <Flame className="w-5 h-5 text-orange-500" />
          <h3 className="font-semibold">热点选题 + 一键生成</h3>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm text-gray-500 mb-1">热点平台</label>
            <select 
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="w-full p-2 border rounded-lg"
            >
              <option value="all">全平台</option>
              <option value="weibo">微博</option>
              <option value="douyin">抖音</option>
              <option value="xiaohongshu">小红书</option>
              <option value="twitter">Twitter</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-500 mb-1">生成数量</label>
            <Input 
              type="number" 
              value={count}
              onChange={(e) => setCount(parseInt(e.target.value) || 5)}
              min={1}
              max={10}
            />
          </div>
        </div>

        {/* 四维权重 */}
        <div className="mb-4">
          <label className="block text-sm text-gray-500 mb-2">四维权重</label>
          <div className="grid grid-cols-4 gap-3">
            <div>
              <label className="text-xs text-gray-400">相关度</label>
              <Input 
                type="number" 
                value={weights.relevance}
                onChange={(e) => setWeights({...weights, relevance: parseFloat(e.target.value) || 0})}
                step={0.1}
                min={0}
                max={1}
              />
            </div>
            <div>
              <label className="text-xs text-gray-400">热度</label>
              <Input 
                type="number" 
                value={weights.hotness}
                onChange={(e) => setWeights({...weights, hotness: parseFloat(e.target.value) || 0})}
                step={0.1}
                min={0}
                max={1}
              />
            </div>
            <div>
              <label className="text-xs text-gray-400">竞争度</label>
              <Input 
                type="number" 
                value={weights.competition}
                onChange={(e) => setWeights({...weights, competition: parseFloat(e.target.value) || 0})}
                step={0.1}
                min={0}
                max={1}
              />
            </div>
            <div>
              <label className="text-xs text-gray-400">转化率</label>
              <Input 
                type="number" 
                value={weights.conversion}
                onChange={(e) => setWeights({...weights, conversion: parseFloat(e.target.value) || 0})}
                step={0.1}
                min={0}
                max={1}
              />
            </div>
          </div>
        </div>

        <Button 
          onClick={handleGenerate}
          disabled={loading}
          className="w-full"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              生成中...
            </>
          ) : (
            <>
              <Zap className="w-4 h-4 mr-2" />
              一键生成
            </>
          )}
        </Button>
      </Card>

      {/* 结果展示 */}
      {results.length > 0 && (
        <div className="space-y-3">
          {results.map((result, idx) => (
            <Card key={idx} className="p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">
                    热度: {result.metadata.hot_score?.toFixed(1) || '-'}
                  </Badge>
                  <Badge variant="outline">
                    相关度: {(result.metadata.relevance_score * 100).toFixed(0)}%
                  </Badge>
                </div>
                <Badge className="bg-orange-100 text-orange-700">
                  得分: {(result.score * 100).toFixed(0)}%
                </Badge>
              </div>
              
              {result.metadata.topic && (
                <div className="text-sm font-medium text-gray-500 mb-2">
                  话题: {result.metadata.topic}
                </div>
              )}
              
              <div className="bg-gray-50 p-3 rounded-lg text-sm whitespace-pre-wrap">
                {result.content}
              </div>
              
              <div className="mt-3 flex justify-end">
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => copyContent(result.content, idx)}
                >
                  {copied === idx.toString() ? (
                    <Check className="w-4 h-4 mr-1" />
                  ) : (
                    <Copy className="w-4 h-4 mr-1" />
                  )}
                  复制
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ==================== 场景二：竞品改写 ====================

export function ScenarioTwoPanel({ ipId }: { ipId: string }) {
  const [competitorContent, setCompetitorContent] = useState('');
  const [platform, setPlatform] = useState('');
  const [rewriteLevel, setRewriteLevel] = useState<'light' | 'medium' | 'heavy'>('medium');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ContentResult | null>(null);
  const [copied, setCopied] = useState(false);

  const handleGenerate = async () => {
    if (!competitorContent.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const data = await api.content.scenarioTwo(ipId, competitorContent, platform, rewriteLevel);
      setResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const copyContent = async () => {
    if (result?.content) {
      await navigator.clipboard.writeText(result.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <PenLine className="w-5 h-5 text-blue-500" />
          <h3 className="font-semibold">竞品爆款改写</h3>
        </div>

        <div className="mb-4">
          <label className="block text-sm text-gray-500 mb-1">竞品内容</label>
          <textarea 
            value={competitorContent}
            onChange={(e) => setCompetitorContent(e.target.value)}
            placeholder="粘贴竞品的爆款内容..."
            className="w-full h-32 p-3 border rounded-lg text-sm resize-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm text-gray-500 mb-1">竞品平台</label>
            <select 
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="w-full p-2 border rounded-lg"
            >
              <option value="">选择平台</option>
              <option value="weibo">微博</option>
              <option value="douyin">抖音</option>
              <option value="xiaohongshu">小红书</option>
              <option value="zhihu">知乎</option>
              <option value="bilibili">B站</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-500 mb-1">改写程度</label>
            <select 
              value={rewriteLevel}
              onChange={(e) =>
                setRewriteLevel(e.target.value as 'light' | 'medium' | 'heavy')
              }
              className="w-full p-2 border rounded-lg"
            >
              <option value="light">轻度改写（保留结构）</option>
              <option value="medium">中度改写（重新组织）</option>
              <option value="heavy">重度改写（完全重构）</option>
            </select>
          </div>
        </div>

        <Button 
          onClick={handleGenerate}
          disabled={loading || !competitorContent.trim()}
          className="w-full"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              分析并改写中...
            </>
          ) : (
            <>
              <PenLine className="w-4 h-4 mr-2" />
              分析爆款 + IP改写
            </>
          )}
        </Button>
      </Card>

      {result && (
        <Card className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Badge className="bg-blue-100 text-blue-700">
                改写程度: {result.metadata.rewrite_level}
              </Badge>
            </div>
            <Badge>
              质量得分: {(result.score * 100).toFixed(0)}%
            </Badge>
          </div>
          
          <div className="bg-gray-50 p-3 rounded-lg text-sm whitespace-pre-wrap">
            {result.content}
          </div>
          
          <div className="mt-3 flex justify-end">
            <Button variant="ghost" size="sm" onClick={copyContent}>
              {copied ? (
                <Check className="w-4 h-4 mr-1" />
              ) : (
                <Copy className="w-4 h-4 mr-1" />
              )}
              复制
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}

// ==================== 场景三：自定义原创 ====================

export function ScenarioThreePanel({ ipId }: { ipId: string }) {
  const [topic, setTopic] = useState('');
  const [keyPoints, setKeyPoints] = useState('');
  const [length, setLength] = useState<'short' | 'medium' | 'long'>('medium');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ContentResult | null>(null);
  const [copied, setCopied] = useState(false);

  const handleGenerate = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const points = keyPoints.trim() 
        ? keyPoints.split('\n').filter(p => p.trim())
        : undefined;
      const data = await api.content.scenarioThree(ipId, topic, points, length);
      setResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const copyContent = async () => {
    if (result?.content) {
      await navigator.clipboard.writeText(result.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <PenLine className="w-5 h-5 text-green-500" />
          <h3 className="font-semibold">自定义原创</h3>
        </div>

        <div className="mb-4">
          <label className="block text-sm text-gray-500 mb-1">话题/主题</label>
          <Input 
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="输入你想写的话题..."
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm text-gray-500 mb-1">
            关键要点 <span className="text-gray-400">(可选，每行一个)</span>
          </label>
          <textarea 
            value={keyPoints}
            onChange={(e) => setKeyPoints(e.target.value)}
            placeholder="要点1&#10;要点2&#10;要点3"
            className="w-full h-24 p-3 border rounded-lg text-sm resize-none"
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm text-gray-500 mb-1">内容长度</label>
          <select 
            value={length}
            onChange={(e) =>
              setLength(e.target.value as 'short' | 'medium' | 'long')
            }
            className="w-full p-2 border rounded-lg"
          >
            <option value="short">短篇 (150-250字)</option>
            <option value="medium">中篇 (300-500字)</option>
            <option value="long">长篇 (600-1000字)</option>
          </select>
        </div>

        <Button 
          onClick={handleGenerate}
          disabled={loading || !topic.trim()}
          className="w-full"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              生成中...
            </>
          ) : (
            <>
              <PenLine className="w-4 h-4 mr-2" />
              生成原创内容
            </>
          )}
        </Button>
      </Card>

      {result && (
        <Card className="p-4">
          <div className="flex items-center justify-between mb-3">
            <Badge className="bg-green-100 text-green-700">
              {result.metadata.length}
            </Badge>
            <Badge>
              质量得分: {(result.score * 100).toFixed(0)}%
            </Badge>
          </div>
          
          <div className="bg-gray-50 p-3 rounded-lg text-sm whitespace-pre-wrap">
            {result.content}
          </div>
          
          <div className="mt-3 flex justify-end">
            <Button variant="ghost" size="sm" onClick={copyContent}>
              {copied ? (
                <Check className="w-4 h-4 mr-1" />
              ) : (
                <Copy className="w-4 h-4 mr-1" />
              )}
              复制
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}

// ==================== 统一导出 ====================

export function ContentGeneratorPanel({ ipId }: { ipId: string }) {
  return (
    <Tabs defaultValue="one" className="w-full">
      <TabsList className="mb-4">
        <TabsTrigger value="one">
          <TrendingUp className="w-4 h-4 mr-2" />
          热点选题
        </TabsTrigger>
        <TabsTrigger value="two">
          <PenLine className="w-4 h-4 mr-2" />
          竞品改写
        </TabsTrigger>
        <TabsTrigger value="three">
          <PenLine className="w-4 h-4 mr-2" />
          自定义原创
        </TabsTrigger>
      </TabsList>

      <TabsContent value="one">
        <ScenarioOnePanel ipId={ipId} />
      </TabsContent>

      <TabsContent value="two">
        <ScenarioTwoPanel ipId={ipId} />
      </TabsContent>

      <TabsContent value="three">
        <ScenarioThreePanel ipId={ipId} />
      </TabsContent>
    </Tabs>
  );
}
