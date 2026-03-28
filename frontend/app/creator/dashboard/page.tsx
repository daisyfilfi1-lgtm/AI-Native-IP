'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { CreatorLayout } from '@/components/creator/CreatorLayout';
import { Card, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { Input } from '@/components/ui/Input';
import { creatorApi, type AgentConfigStatus } from '@/lib/api/creator';
import type { TopicCard, StyleType, RemixRecommendationItem } from '@/types/creator';
import { 
  Sparkles, 
  TrendingUp, 
  Target, 
  Zap,
  ArrowRight,
  Mic,
  FileText,
  Loader2,
  Link as LinkIcon,
  Brain,
  Shield,
  BarChart3,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Settings,
  ChevronRight,
  Flame,
  Upload,
  FileText as Keyboard,
  Wand2,
  Lightbulb,
  Pencil,
  ExternalLink
} from 'lucide-react';
import Link from 'next/link';

import { useCreatorIp } from '@/contexts/CreatorIpContext';
import { ThirdPartyExtractor } from '@/components/creator/ThirdPartyExtractor';

/** 接口仍要求 style 字段；生成侧以 IP 风格画像为准 */
const DEFAULT_WORKFLOW_STYLE: StyleType = 'angry';

// Agent配置状态组件
function AgentStatusCard({ 
  name, 
  icon: Icon, 
  status, 
  config 
}: { 
  name: string; 
  icon: any; 
  status: 'ready' | 'configuring' | 'error';
  config: string[];
}) {
  const statusColors = {
    ready: 'bg-accent-green/10 text-accent-green border-accent-green/20',
    configuring: 'bg-accent-yellow/10 text-accent-yellow border-accent-yellow/20',
    error: 'bg-accent-red/10 text-accent-red border-accent-red/20'
  };

  const statusLabels = {
    ready: '已就绪',
    configuring: '配置中',
    error: '需配置'
  };

  return (
    <div className={cn(
      "p-3 rounded-xl border flex items-center gap-3",
      statusColors[status]
    )}>
      <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center">
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{name}</span>
          <Badge variant={status === 'ready' ? 'success' : status === 'configuring' ? 'warning' : 'danger'} size="sm">
            {statusLabels[status]}
          </Badge>
        </div>
        <p className="text-xs opacity-80 truncate">{config.join(' · ')}</p>
      </div>
    </div>
  );
}

/** 仅允许 http(s)，避免 href 无效导致「点不进去」 */
function safeExternalHref(url: string | undefined): string | null {
  if (!url || typeof url !== 'string') return null;
  const t = url.trim();
  if (!t.startsWith('http://') && !t.startsWith('https://')) return null;
  try {
    return new URL(t).href;
  } catch {
    return null;
  }
}

// 选题卡片组件
function TopicCardComponent({ 
  topic, 
  index, 
  onGenerate,
  isGenerating 
}: { 
  topic: TopicCard; 
  index: number;
  onGenerate: (topic: TopicCard) => void;
  isGenerating: boolean;
}) {
  const sourceHref = safeExternalHref(topic.sourceUrl);
  const scoreColor = topic.score >= 4.8 ? 'text-accent-green' : topic.score >= 4.5 ? 'text-accent-yellow' : 'text-foreground';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
    >
      <Card className="h-full flex flex-col hover:border-primary-500/50 transition-all group">
        {/* Rank & Score */}
        <div className="p-5 pb-0 flex items-start justify-between">
          <div className={cn(
            "w-10 h-10 rounded-xl flex items-center justify-center font-bold text-lg",
            index === 0 ? "bg-gradient-to-br from-yellow-400 to-yellow-600 text-white" :
            index === 1 ? "bg-gradient-to-br from-gray-300 to-gray-500 text-white" :
            index === 2 ? "bg-gradient-to-br from-amber-600 to-amber-800 text-white" :
            "bg-background-tertiary text-foreground-secondary"
          )}>
            {index + 1}
          </div>
          <div className="text-right">
            <div className={cn("text-2xl font-bold", scoreColor)}>{topic.score.toFixed(1)}</div>
            <div className="text-xs text-foreground-tertiary">策略评分</div>
          </div>
        </div>

        <div className="p-5 flex-1 flex flex-col">
          {/* Title - IP改写后 */}
          <h3 className="text-lg font-semibold text-foreground mb-2 line-clamp-2 group-hover:text-primary-400 transition-colors">
            {topic.title}
          </h3>
          
          {/* Original Title - 原标题 */}
          {topic.originalTitle && topic.originalTitle !== topic.title && (
            <div className="mb-3 p-2 bg-background-tertiary/50 rounded-lg">
              <div className="text-xs text-foreground-tertiary mb-1">原热点</div>
              <div className="text-sm text-foreground-secondary line-clamp-1">{topic.originalTitle}</div>
            </div>
          )}
          
          {/* Source Link - 原链接（后端未返回合法绝对 URL 时不展示，避免无效点击） */}
          {sourceHref && (
            <a 
              href={sourceHref}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 mb-3 text-xs text-primary-400 hover:text-primary-300 transition-colors"
              onClick={(e) => e.stopPropagation()}
            >
              <LinkIcon className="w-3 h-3" />
              查看原链接
              <ExternalLink className="w-3 h-3" />
            </a>
          )}

          {/* Competitor Source - V4 竞品来源 */}
          {topic.competitorName && (
            <div className="mb-3 p-2.5 bg-accent-pink/5 border border-accent-pink/20 rounded-lg">
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-1.5">
                  <Target className="w-3.5 h-3.5 text-accent-pink" />
                  <span className="text-xs font-medium text-accent-pink">竞品来源</span>
                </div>
                {topic.remixPotential === 'high' && (
                  <Badge variant="success" size="sm">高仿写价值</Badge>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-foreground">{topic.competitorName}</span>
                {topic.competitorPlatform && (
                  <Badge variant={topic.competitorPlatform === 'douyin' ? 'primary' : 'secondary'} size="sm">
                    {topic.competitorPlatform === 'douyin' ? '抖音' : '小红书'}
                  </Badge>
                )}
              </div>
              {topic.originalPlays && (
                <div className="mt-1 text-xs text-foreground-tertiary">
                  原视频播放量: <span className="text-accent-pink font-medium">{topic.originalPlays}</span>
                </div>
              )}
            </div>
          )}

          {/* Match Reason */}
          <div className="flex items-center gap-2 mb-3 text-xs">
            <Brain className="w-3.5 h-3.5 text-primary-400" />
            <span className="text-foreground-secondary">{topic.reason}</span>
          </div>

          {/* Tags */}
          <div className="flex flex-wrap gap-1.5 mb-4">
            {topic.tags.map(tag => (
              <span key={tag} className="px-2 py-0.5 bg-background-tertiary text-foreground-secondary text-xs rounded-full">
                {tag}
              </span>
            ))}
          </div>

          {/* Prediction */}
          <div className="space-y-2 mb-4 p-3 bg-background-tertiary/50 rounded-xl">
            <div className="flex items-center justify-between text-sm">
              <span className="text-foreground-secondary">预估播放</span>
              <span className="font-semibold text-foreground">{topic.estimatedViews}</span>
            </div>
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-foreground-tertiary">预估完播率</span>
                <span className="text-foreground-secondary">{topic.estimatedCompletion}%</span>
              </div>
              <Progress value={topic.estimatedCompletion} size="sm" variant="gradient" />
            </div>
          </div>

          {/* Generate Button */}
          <Button 
            className="w-full mt-auto"
            leftIcon={isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            onClick={() => onGenerate(topic)}
            isLoading={isGenerating}
            disabled={isGenerating}
          >
            {isGenerating ? '生成中...' : '一键生成'}
          </Button>
        </div>
      </Card>
    </motion.div>
  );
}

// 爆款原创 - 输入方式切换组件
function InputModeSelector({ 
  mode, 
  onChange 
}: { 
  mode: 'text' | 'voice' | 'file';
  onChange: (mode: 'text' | 'voice' | 'file') => void;
}) {
  const modes = [
    { id: 'text' as const, label: '文字输入', icon: Keyboard, desc: '直接输入想法' },
    { id: 'voice' as const, label: '语音录制', icon: Mic, desc: '边说边录' },
    { id: 'file' as const, label: '上传文件', icon: Upload, desc: '音频/视频文件' },
  ];

  return (
    <div className="grid grid-cols-3 gap-3 mb-6">
      {modes.map(({ id, label, icon: Icon, desc }) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          className={cn(
            "p-4 rounded-xl border-2 transition-all text-left",
            mode === id
              ? "border-primary-500 bg-primary-500/10"
              : "border-border bg-background-tertiary hover:border-border-hover"
          )}
        >
          <div className={cn(
            "w-10 h-10 rounded-lg flex items-center justify-center mb-3",
            mode === id ? "bg-primary-500 text-white" : "bg-background-elevated text-foreground-secondary"
          )}>
            <Icon className="w-5 h-5" />
          </div>
          <div className="font-medium text-foreground text-sm">{label}</div>
          <div className="text-xs text-foreground-tertiary mt-1">{desc}</div>
        </button>
      ))}
    </div>
  );
}

// 主页面组件
export default function CreatorDashboardPage() {
  const router = useRouter();
  const { ipId, loading: ipCtxLoading, needsLogin, noIp, error: ipCtxError } = useCreatorIp();
  const [activeTab, setActiveTab] = useState('recommended');
  const [topics, setTopics] = useState<TopicCard[]>([]);
  const [agentStatus, setAgentStatus] = useState<AgentConfigStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [generatingTopicId, setGeneratingTopicId] = useState<string | null>(null);
  
  // 仿写爆款相关
  const [remixUrl, setRemixUrl] = useState('');
  const [isRemixing, setIsRemixing] = useState(false);
  const [remixError, setRemixError] = useState<string | null>(null);
  const [remixRecs, setRemixRecs] = useState<RemixRecommendationItem[]>([]);
  const [remixRecLoading, setRemixRecLoading] = useState(false);
  // 手动输入模式（当自动提取失败时使用）
  const [remixManualMode, setRemixManualMode] = useState(false);
  const [remixManualText, setRemixManualText] = useState('');
  // 显示第三方工具提取器
  const [showThirdPartyExtractor, setShowThirdPartyExtractor] = useState(false);

  const loadRemixRecommendations = useCallback(async () => {
    if (!ipId) return;
    setRemixRecLoading(true);
    try {
      const items = await creatorApi.getRemixRecommendations(ipId);
      setRemixRecs(items);
    } catch (e) {
      console.error('Remix recommendations failed:', e);
      setRemixRecs([]);
    } finally {
      setRemixRecLoading(false);
    }
  }, [ipId]);
  
  // 爆款原创相关
  const [viralInputMode, setViralInputMode] = useState<'text' | 'voice' | 'file'>('text');
  const [isRecording, setIsRecording] = useState(false);
  const [viralText, setViralText] = useState('');
  const [isGeneratingViral, setIsGeneratingViral] = useState(false);
  const [viralConfig, setViralConfig] = useState({
    scriptTemplate: 'opinion', // opinion | process | knowledge | story | custom
    customScriptHint: '',
    viralElements: ['auto'], // 默认系统自动配置
    targetDuration: 60, // 目标时长（秒）
  });

  useEffect(() => {
    if (ipCtxLoading) return;
    if (!ipId) {
      setTopics([]);
      setAgentStatus(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [topicsRes, statusRes] = await Promise.allSettled([
          creatorApi.getRecommendedTopics(ipId),
          creatorApi.getAgentConfigStatus(),
        ]);
        if (cancelled) return;
        if (topicsRes.status === 'fulfilled') {
          setTopics(topicsRes.value);
        } else {
          console.error('Recommended topics failed:', topicsRes.reason);
          setTopics([]);
        }
        if (statusRes.status === 'fulfilled') {
          setAgentStatus(statusRes.value);
        } else {
          console.error('Agent status failed:', statusRes.reason);
          setAgentStatus(null);
        }
      } catch (error) {
        console.error('Failed to load data:', error);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ipId, ipCtxLoading]);

  useEffect(() => {
    if (activeTab !== 'remix' || !ipId) return;
    void loadRemixRecommendations();
  }, [activeTab, loadRemixRecommendations, ipId]);

  // 场景一：推荐选题生成
  const handleGenerateFromTopic = async (topic: TopicCard) => {
    if (!ipId) return;
    setGeneratingTopicId(topic.id);
    try {
      const result = await creatorApi.generateFromTopic(
        topic.id,
        topic.title,
        DEFAULT_WORKFLOW_STYLE,
        ipId
      );
      router.push(`/creator/generate?id=${result.id}&type=topic`);
    } catch (error) {
      console.error('Generate failed:', error);
      setGeneratingTopicId(null);
    }
  };

  // 场景二：仿写爆款
  const handleRemix = async () => {
    if (!ipId || !remixUrl.trim()) {
      setRemixError('请输入有效的竞品链接');
      return;
    }
    
    // 基础链接格式校验（允许手动输入模式）
    const url = remixUrl.trim();
    const isManualMode = url.startsWith('[MANUAL_TEXT]');
    if (!isManualMode && !url.startsWith('http://') && !url.startsWith('https://')) {
      setRemixError('链接格式不正确，必须以 http:// 或 https:// 开头');
      return;
    }
    
    setRemixError(null);
    setShowThirdPartyExtractor(false);
    setIsRemixing(true);
    
    try {
      const result = await creatorApi.generateFromRemix(url, DEFAULT_WORKFLOW_STYLE, ipId);
      
      // 双重检查：即使API调用成功，也要确认状态
      if (result.status === 'failed') {
        throw new Error(result.error || '仿写生成失败');
      }
      
      // 成功，跳转到生成结果页
      router.push(`/creator/generate?id=${result.id}&type=remix`);
    } catch (error) {
      console.error('Remix failed:', error);
      const msg = error instanceof Error 
        ? error.message 
        : '仿写请求失败，请检查网络或稍后重试';
      setRemixError(msg);
      setIsRemixing(false);
    }
  };

  // 场景三：爆款原创（工业化流水线生成）
  const handleViralGenerate = async () => {
    if (!ipId || !viralText.trim()) return;
    setIsGeneratingViral(true);
    try {
      const useAutoElements =
        viralConfig.viralElements.includes('auto') ||
        viralConfig.viralElements.includes('system_auto');
      // 调用工业化爆款生产流水线
      const result = await creatorApi.generateViralOriginal({
        ipId,
        input: viralText,
        inputMode: viralInputMode,
        scriptTemplate: viralConfig.scriptTemplate,
        viralElements: useAutoElements ? ['auto'] : viralConfig.viralElements,
        targetDuration: viralConfig.targetDuration,
        style: DEFAULT_WORKFLOW_STYLE,
        customScriptHint:
          viralConfig.scriptTemplate === 'custom'
            ? viralConfig.customScriptHint.trim() || undefined
            : undefined,
      });
      router.push(`/creator/generate?id=${result.id}&type=original`);
    } catch (error) {
      console.error('Viral generate failed:', error);
      setIsGeneratingViral(false);
    }
  };

  // 检查Agent配置状态
  const isStrategyReady = agentStatus?.strategy.status === 'ready';
  const isMemoryReady = agentStatus?.memory.status === 'ready';
  const isGenerationReady = agentStatus?.generation.status === 'ready';
  const isRemixReady = agentStatus?.remix.status === 'ready';
  const isComplianceReady = agentStatus?.compliance.status === 'ready';
  /** agent-status 拉取失败时 agentStatus 为 null，不阻断仿写（后端仍会校验） */
  const remixAgentsBlock =
    agentStatus != null && (!isRemixReady || !isMemoryReady);

  const allReady = isStrategyReady && isMemoryReady && isGenerationReady && isComplianceReady;

  return (
    <CreatorLayout>
      {ipCtxError && (
        <div className="mb-4 p-3 rounded-lg bg-accent-red/10 border border-accent-red/20 text-sm text-accent-red">
          {ipCtxError}
        </div>
      )}
      {needsLogin && (
        <div className="mb-4 p-4 rounded-xl bg-background-tertiary border border-border text-sm text-foreground-secondary">
          请先{' '}
          <Link href="/login" className="text-primary-400 font-medium hover:underline">
            登录
          </Link>
          ，以加载你账号下已绑定的 IP；创作将使用该 IP。
        </div>
      )}
      {noIp && (
        <div className="mb-4 p-4 rounded-xl bg-background-tertiary border border-border text-sm text-foreground-secondary">
          当前账号下还没有 IP。请前往{' '}
          <Link href="/ip" className="text-primary-400 font-medium hover:underline">
            IP 管理
          </Link>
          创建 IP，并将拥有者设为当前登录用户。
        </div>
      )}

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground mb-2">
          今日工作台
        </h1>
        <p className="text-foreground-secondary">
          选择创作方式，AI将调用已配置的Agent为你生成内容
        </p>
      </div>

      {/* Agent状态监控 */}
      <Card className="mb-6">
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Settings className="w-4 h-4 text-foreground-secondary" />
              <span className="text-sm font-medium text-foreground">Agent配置状态</span>
            </div>
            <Link href="/agents" className="text-xs text-primary-400 hover:text-primary-300 flex items-center gap-1">
              前往配置 <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
          
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <AgentStatusCard 
              name="Strategy" 
              icon={BarChart3} 
              status={agentStatus?.strategy.status || 'configuring'}
              config={agentStatus?.strategy.config || ['评分权重', '竞品监控']}
            />
            <AgentStatusCard 
              name="Memory" 
              icon={Brain} 
              status={agentStatus?.memory.status || 'configuring'}
              config={agentStatus?.memory.config || ['标签体系', '检索策略']}
            />
            <AgentStatusCard 
              name="Remix" 
              icon={RefreshCw} 
              status={agentStatus?.remix.status || 'configuring'}
              config={agentStatus?.remix.config || ['解构规则', '原创度']}
            />
            <AgentStatusCard 
              name="Generation" 
              icon={Sparkles} 
              status={agentStatus?.generation.status || 'configuring'}
              config={agentStatus?.generation.config || ['风格训练', '口头禅']}
            />
            <AgentStatusCard 
              name="Compliance" 
              icon={Shield} 
              status={agentStatus?.compliance.status || 'configuring'}
              config={agentStatus?.compliance.config || ['敏感词库', '平台规则']}
            />
          </div>

          {!allReady && (
            <div className="mt-3 p-3 bg-accent-yellow/10 border border-accent-yellow/20 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-accent-yellow flex-shrink-0" />
              <p className="text-xs text-accent-yellow">
                部分Agent未配置完成，可能影响生成质量。建议先完成配置再创作。
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* 创作方式切换 */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3 mb-6">
          <TabsTrigger value="recommended" className="gap-2">
            <Sparkles className="w-4 h-4" />
            推荐选题
            <Badge variant="primary" size="sm">Strategy</Badge>
          </TabsTrigger>
          <TabsTrigger value="remix" className="gap-2">
            <RefreshCw className="w-4 h-4" />
            仿写爆款
            <Badge variant="primary" size="sm">Remix</Badge>
          </TabsTrigger>
          <TabsTrigger value="viral" className="gap-2">
            <Flame className="w-4 h-4" />
            爆款原创
            <Badge variant="success" size="sm">NEW</Badge>
          </TabsTrigger>
        </TabsList>

        {/* 场景一：推荐选题 */}
        <TabsContent value="recommended">
          <div className="space-y-6">
            {/* 场景说明 */}
            <div className="p-4 bg-background-tertiary/50 rounded-xl border border-border">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary-500/10 flex items-center justify-center flex-shrink-0">
                  <BarChart3 className="w-5 h-5 text-primary-400" />
                </div>
                <div>
                  <h3 className="font-medium text-foreground mb-1">Strategy Agent 智能推荐</h3>
                  <p className="text-sm text-foreground-secondary">
                    基于<span className="text-primary-400">四维评分算法</span>（流量/变现/契合度/成本），
                    从监控的竞品中筛选出最适合你的选题，并匹配Memory Agent中的相关素材。
                  </p>
                </div>
              </div>
            </div>

            {/* 选题卡片 */}
            {ipCtxLoading || loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {topics.map((topic, index) => (
                  <TopicCardComponent
                    key={topic.id}
                    topic={topic}
                    index={index}
                    onGenerate={handleGenerateFromTopic}
                    isGenerating={generatingTopicId === topic.id}
                  />
                ))}
              </div>
            )}

            {!isStrategyReady && (
              <div className="text-center py-8">
                <AlertCircle className="w-12 h-12 mx-auto mb-3 text-accent-yellow" />
                <p className="text-foreground-secondary mb-3">Strategy Agent 未配置完成</p>
                <Button variant="secondary" leftIcon={<Settings className="w-4 h-4" />}>
                  前往配置评分权重
                </Button>
              </div>
            )}
          </div>
        </TabsContent>

        {/* 场景二：仿写爆款 */}
        <TabsContent value="remix">
          <div className="max-w-2xl mx-auto">
            {/* 场景说明 */}
            <div className="p-4 bg-background-tertiary/50 rounded-xl border border-border mb-6">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-accent-pink/10 flex items-center justify-center flex-shrink-0">
                  <RefreshCw className="w-5 h-5 text-accent-pink" />
                </div>
                <div>
                  <h3 className="font-medium text-foreground mb-1">Remix Agent 结构仿写</h3>
                  <p className="text-sm text-foreground-secondary">
                    输入竞品链接，Remix Agent会<span className="text-accent-pink">解构其结构</span>（钩子/情绪/论证），
                    然后调用Memory Agent<span className="text-accent-pink">替换为你的素材</span>，
                    最后Generation Agent用<span className="text-accent-pink">你的风格重写</span>。
                  </p>
                </div>
              </div>
            </div>

            <Card>
              <div className="p-6 space-y-6">
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div>
                      <h4 className="text-sm font-medium text-foreground">低粉爆款推荐（TikHub）</h4>
                      <p className="text-xs text-foreground-tertiary mt-0.5">
                        按 IP 画像 + <span className="text-accent-pink/90">TIKHUB_REMIX_EXTRA_KEYWORDS</span> 匹配标题后排序
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      leftIcon={
                        remixRecLoading ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <RefreshCw className="w-3.5 h-3.5" />
                        )
                      }
                      onClick={() => void loadRemixRecommendations()}
                      disabled={remixRecLoading}
                    >
                      刷新
                    </Button>
                  </div>
                  {remixRecLoading && remixRecs.length === 0 ? (
                    <div className="flex items-center justify-center py-8 text-foreground-tertiary text-sm">
                      <Loader2 className="w-5 h-5 animate-spin mr-2" />
                      拉取低粉榜…
                    </div>
                  ) : remixRecs.length === 0 ? (
                    <p className="text-sm text-foreground-tertiary py-4 text-center rounded-xl bg-background-tertiary/50 border border-border">
                      暂无推荐。请确认后端已配置 TIKHUB_API_KEY，且 TikHub 低粉榜接口有数据；关键词仅影响排序与「命中」文案。
                    </p>
                  ) : (
                    <ul className="space-y-2 max-h-64 overflow-y-auto pr-1">
                      {remixRecs.map((r, idx) => (
                        <li
                          key={`${r.url}-${idx}`}
                          className="flex items-start gap-3 p-3 rounded-xl bg-background-tertiary/80 border border-border"
                        >
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-foreground line-clamp-2">{r.title}</p>
                            <p className="text-xs text-foreground-tertiary mt-1 line-clamp-2">{r.reason}</p>
                          </div>
                          <Badge variant="primary" size="sm" className="shrink-0">
                            {r.platform === 'douyin' ? '抖音' : '小红书'}
                          </Badge>
                          <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            className="shrink-0"
                            onClick={() => setRemixUrl(r.url)}
                          >
                            填入
                          </Button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {/* URL输入 */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    竞品视频链接
                  </label>
                  <div className="flex gap-3">
                    <div className="flex-1 relative">
                      <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-tertiary" />
                      <input
                        type="text"
                        value={remixUrl}
                        onChange={(e) => setRemixUrl(e.target.value)}
                        placeholder="粘贴抖音/视频号/小红书链接（含 xhslink.com 短链）…"
                        className="w-full pl-10 pr-4 py-3 bg-background-tertiary border border-border rounded-xl text-foreground placeholder:text-foreground-muted focus:outline-none focus:border-primary-500/50"
                      />
                    </div>
                  </div>
                </div>

                {/* 配置检查 */}
                <div className="p-4 bg-background-tertiary rounded-xl space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    {isRemixReady ? (
                      <CheckCircle2 className="w-4 h-4 text-accent-green" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-accent-yellow" />
                    )}
                    <span className={isRemixReady ? 'text-accent-green' : 'text-accent-yellow'}>
                      Remix Agent: {isRemixReady ? '解构规则已配置' : '需配置解构规则'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    {isMemoryReady ? (
                      <CheckCircle2 className="w-4 h-4 text-accent-green" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-accent-yellow" />
                    )}
                    <span className={isMemoryReady ? 'text-accent-green' : 'text-accent-yellow'}>
                      Memory Agent: {isMemoryReady ? '素材库已就绪' : '需配置标签体系'}
                    </span>
                  </div>
                </div>

                {remixError && (
                  <div className="p-4 rounded-xl bg-accent-red/10 border border-accent-red/25">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 text-accent-red flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-accent-red mb-2">仿写失败</p>
                        <p className="text-sm text-accent-red/80 whitespace-pre-wrap">{remixError}</p>
                        
                        {/* 根据错误类型显示解决建议 */}
                        {remixError.includes('TIKHUB_API_KEY') && (
                          <div className="mt-3 p-3 rounded-lg bg-background-tertiary/50 text-xs text-foreground-secondary">
                            <p className="font-medium text-foreground mb-1">💡 解决方案：</p>
                            <p>请确保后端已配置 TIKHUB_API_KEY 环境变量，或联系管理员开通 TikHub 服务。</p>
                          </div>
                        )}
                        {remixError.includes('链接') && (remixError.includes('格式') || remixError.includes('空')) && (
                          <div className="mt-3 p-3 rounded-lg bg-background-tertiary/50 text-xs text-foreground-secondary">
                            <p className="font-medium text-foreground mb-1">💡 正确格式示例：</p>
                            <ul className="space-y-1">
                              <li>• 抖音: https://v.douyin.com/xxxxx 或 https://www.douyin.com/video/xxxxx</li>
                              <li>• 小红书: https://xhslink.com/xxxxx</li>
                            </ul>
                          </div>
                        )}
                        {remixError.includes('提取') && (
                          <>
                            <div className="mt-3 p-3 rounded-lg bg-background-tertiary/50 text-xs text-foreground-secondary">
                              <p className="font-medium text-foreground mb-1">💡 可能原因：</p>
                              <ul className="space-y-1">
                                <li>• 视频链接已失效或被删除</li>
                                <li>• 视频设置了隐私权限</li>
                                <li>• 平台接口暂时不可用</li>
                              </ul>
                            </div>
                            
                            {/* 使用第三方工具按钮 */}
                            <button
                              type="button"
                              onClick={() => setShowThirdPartyExtractor(true)}
                              className="mt-3 flex items-center gap-2 px-3 py-2 bg-primary-500/10 text-primary-400 rounded-lg text-xs hover:bg-primary-500/20 transition-colors"
                            >
                              <span>🔍</span>
                              <span>使用第三方工具提取文案</span>
                            </button>
                          </>
                        )}
                        
                        {/* 手动输入模式切换 */}
                        <button
                          type="button"
                          onClick={() => {
                            setRemixManualMode(!remixManualMode);
                            setShowThirdPartyExtractor(false);
                          }}
                          className="mt-3 text-xs text-primary-400 hover:text-primary-300 underline"
                        >
                          {remixManualMode ? '← 返回链接提取模式' : '直接粘贴文案 →'}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* 手动输入模式 */}
                {remixManualMode && (
                  <div className="p-4 rounded-xl bg-background-tertiary border border-border">
                    <label className="block text-sm font-medium text-foreground mb-2">
                      手动粘贴竞品文案
                    </label>
                    <p className="text-xs text-foreground-secondary mb-3">
                      当自动提取失败时，你可以直接复制视频的标题和文案粘贴到这里。
                    </p>
                    <textarea
                      value={remixManualText}
                      onChange={(e) => setRemixManualText(e.target.value)}
                      placeholder="粘贴视频标题和文案..."
                      rows={6}
                      className="w-full p-3 bg-background-elevated border border-border rounded-lg text-foreground placeholder:text-foreground-muted resize-none focus:outline-none focus:border-primary-500/50"
                    />
                    <div className="flex justify-between items-center mt-3">
                      <button
                        type="button"
                        onClick={() => {
                          setRemixManualMode(false);
                          setRemixManualText('');
                        }}
                        className="text-xs text-foreground-secondary hover:text-foreground"
                      >
                        取消
                      </button>
                      <Button
                        size="sm"
                        onClick={() => {
                          // 使用手动文本作为 "链接" 传递给后端
                          // 这里我们会在后端添加特殊处理
                          setRemixUrl(`[MANUAL_TEXT]${remixManualText}`);
                          setRemixManualMode(false);
                        }}
                        disabled={!remixManualText.trim()}
                      >
                        使用此文案
                      </Button>
                    </div>
                  </div>
                )}
                
                {/* 第三方工具提取器 */}
                {showThirdPartyExtractor && (
                  <ThirdPartyExtractor
                    videoUrl={remixUrl}
                    onTextExtracted={(text) => {
                      // 使用提取的文案
                      setRemixUrl(`[MANUAL_TEXT]${text}`);
                      setShowThirdPartyExtractor(false);
                      // 自动触发仿写
                      setTimeout(() => {
                        handleRemix();
                      }, 100);
                    }}
                  />
                )}

                {/* 生成按钮 */}
                <Button
                  className="w-full"
                  size="lg"
                  leftIcon={isRemixing ? <Loader2 className="w-5 h-5 animate-spin" /> : <RefreshCw className="w-5 h-5" />}
                  onClick={handleRemix}
                  isLoading={isRemixing}
                  disabled={!remixUrl.trim() || isRemixing || remixAgentsBlock}
                >
                  {isRemixing ? '解构与生成中...' : '开始仿写'}
                </Button>
              </div>
            </Card>
          </div>
        </TabsContent>

        {/* 场景三：爆款原创（工业化流水线） */}
        <TabsContent value="viral">
          <div className="max-w-3xl mx-auto">
            {/* 场景说明 - 工业化爆款生产流水线 */}
            <div className="p-4 bg-gradient-to-r from-orange-500/10 to-red-500/10 rounded-xl border border-orange-500/20 mb-6">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center flex-shrink-0">
                  <Flame className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium text-foreground">爆款原创 · 工业化流水线</h3>
                    <Badge variant="success" size="sm">专业级</Badge>
                  </div>
                  <p className="text-sm text-foreground-secondary">
                    说出你的想法，AI将使用<span className="text-orange-400">八大爆款元素</span>和<span className="text-orange-400">自动结构路由</span>，
                    通过7步精加工，为你生成原创爆款。专业级工业化内容生产系统。
                  </p>
                  <p className="text-xs text-orange-300 mt-1">
                    已上线：自由创作（AI自动结构）
                  </p>
                </div>
              </div>
            </div>

            <Card>
              <div className="p-6 space-y-6">
                {/* 输入方式切换 */}
                <InputModeSelector mode={viralInputMode} onChange={setViralInputMode} />

                {/* 根据输入模式显示不同UI */}
                <AnimatePresence mode="wait">
                  {viralInputMode === 'voice' && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                    >
                      {/* 录音按钮 */}
                      <button
                        onClick={() => setIsRecording(!isRecording)}
                        className={cn(
                          "w-full py-8 rounded-xl border-2 border-dashed transition-all flex flex-col items-center gap-3",
                          isRecording
                            ? "border-accent-red bg-accent-red/10 animate-pulse"
                            : "border-border hover:border-primary-500/50 bg-background-tertiary"
                        )}
                      >
                        <div className={cn(
                          "w-16 h-16 rounded-full flex items-center justify-center transition-all",
                          isRecording ? "bg-accent-red" : "bg-primary-500"
                        )}>
                          <Mic className="w-8 h-8 text-white" />
                        </div>
                        <span className={cn(
                          "font-medium",
                          isRecording ? "text-accent-red" : "text-foreground"
                        )}>
                          {isRecording ? '正在录音... 点击停止' : '点击开始录音'}
                        </span>
                      </button>
                    </motion.div>
                  )}

                  {viralInputMode === 'file' && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="p-6 rounded-xl border-2 border-dashed border-border bg-background-tertiary text-center"
                    >
                      <Upload className="w-10 h-10 mx-auto mb-3 text-foreground-tertiary" />
                      <p className="text-sm text-foreground-secondary mb-2">拖拽音频/视频文件到此处</p>
                      <p className="text-xs text-foreground-muted mb-4">支持 MP3, WAV, MP4, MOV (最大50MB)</p>
                      <Button variant="secondary" size="sm">选择文件</Button>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* 文本编辑区（所有模式都有） */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    {viralInputMode === 'text' ? '输入你的想法' : '识别结果 / 补充内容'}
                  </label>
                  <textarea
                    value={viralText}
                    onChange={(e) => setViralText(e.target.value)}
                    placeholder={
                      viralInputMode === 'text' 
                        ? "例如：我想讲一个关于创业失败但又重新站起来的故事，希望能引起同龄人的共鸣..."
                        : "识别的文字将显示在这里，你可以编辑补充..."
                    }
                    rows={5}
                    className="w-full p-4 bg-background-tertiary border border-border rounded-xl text-foreground placeholder:text-foreground-muted resize-none focus:outline-none focus:border-primary-500/50"
                  />
                </div>

                {/* 工业化流水线配置 */}
                <div className="p-4 bg-background-tertiary rounded-xl space-y-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Wand2 className="w-4 h-4 text-orange-400" />
                    <span className="text-sm font-medium text-foreground">流水线配置</span>
                    <span className="text-xs text-foreground-tertiary ml-auto">智能推荐，可手动调整</span>
                  </div>

                  {/* 脚本模板选择 */}
                  <div>
                    <label className="block text-xs text-foreground-secondary mb-2">脚本模板（四大模板 + 自由创作）</label>
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { id: 'opinion', name: '说观点', desc: '吸真粉/高互动', icon: Lightbulb },
                        { id: 'process', name: '晒过程', desc: '强转化/近变现', icon: RefreshCw },
                        { id: 'knowledge', name: '教知识', desc: '精准粉/高客单', icon: Brain },
                        { id: 'story', name: '讲故事', desc: '立人设/高信任', icon: FileText },
                        { id: 'custom', name: '自由创作', desc: '按话题自动策划结构', icon: Pencil },
                      ].map((template) => (
                        <button
                          key={template.id}
                          type="button"
                          onClick={() =>
                            setViralConfig((prev) => ({
                              ...prev,
                              scriptTemplate: template.id,
                            }))
                          }
                          className={cn(
                            'flex items-center gap-2 p-2 rounded-lg border text-left transition-all',
                            template.id === 'custom' && 'col-span-2',
                            viralConfig.scriptTemplate === template.id
                              ? 'border-orange-500 bg-orange-500/10'
                              : 'border-border hover:border-border-hover'
                          )}
                        >
                          <template.icon className="w-4 h-4 text-foreground-secondary shrink-0" />
                          <div className="min-w-0">
                            <div className="text-sm font-medium text-foreground">{template.name}</div>
                            <div className="text-xs text-foreground-tertiary">{template.desc}</div>
                          </div>
                        </button>
                      ))}
                    </div>
                    {viralConfig.scriptTemplate === 'custom' && (
                      <div className="mt-2">
                        <label
                          htmlFor="creator-clean-custom-script-hint"
                          className="block text-xs text-foreground-secondary mb-1"
                        >
                          高级可选：补充结构偏好（可不填，系统会自动策划）
                        </label>
                        <textarea
                          id="creator-clean-custom-script-hint"
                          name="customScriptHint"
                          value={viralConfig.customScriptHint}
                          onChange={(e) =>
                            setViralConfig((prev) => ({
                              ...prev,
                              customScriptHint: e.target.value,
                            }))
                          }
                          placeholder="可选，例如：先讲失败经历，再给三条步骤，结尾引导评论"
                          rows={3}
                          className="w-full p-3 bg-background-elevated border border-border rounded-lg text-sm text-foreground placeholder:text-foreground-muted resize-none focus:outline-none focus:border-primary-500/50"
                        />
                      </div>
                    )}
                  </div>

                  {/* 爆款元素选择 */}
                  <div>
                    <label className="block text-xs text-foreground-secondary mb-2">八大爆款元素（默认系统自动，可手动改）</label>
                    <div className="mb-2">
                      <button
                        type="button"
                        onClick={() =>
                          setViralConfig((prev) => ({
                            ...prev,
                            viralElements:
                              prev.viralElements.includes('auto') || prev.viralElements.includes('system_auto')
                                ? []
                                : ['auto'],
                          }))
                        }
                        className={cn(
                          'px-2 py-1 rounded-md text-xs border transition-all',
                          viralConfig.viralElements.includes('auto') || viralConfig.viralElements.includes('system_auto')
                            ? 'border-orange-500 bg-orange-500/10 text-orange-300'
                            : 'border-border text-foreground-secondary hover:border-border-hover'
                        )}
                      >
                        {viralConfig.viralElements.includes('auto') || viralConfig.viralElements.includes('system_auto')
                          ? '系统自动配置：开启'
                          : '系统自动配置：关闭'}
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {[
                        { id: 'cost', name: '成本', emoji: '💰' },
                        { id: 'crowd', name: '人群', emoji: '👥' },
                        { id: 'weird', name: '奇葩', emoji: '🤪' },
                        { id: 'worst', name: '最差', emoji: '⛔' },
                        { id: 'contrast', name: '反差', emoji: '🔄' },
                        { id: 'nostalgia', name: '怀旧', emoji: '📷' },
                        { id: 'hormone', name: '荷尔蒙', emoji: '💖' },
                        { id: 'top', name: '头牌', emoji: '👑' },
                      ].map((element) => (
                        <button
                          key={element.id}
                          onClick={() => {
                            setViralConfig(prev => ({
                              ...prev,
                              viralElements: prev.viralElements.includes(element.id)
                                ? prev.viralElements.filter(e => e !== element.id && e !== 'auto' && e !== 'system_auto')
                                : [...prev.viralElements.filter(e => e !== 'auto' && e !== 'system_auto'), element.id]
                            }));
                          }}
                          className={cn(
                            "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition-all",
                            viralConfig.viralElements.includes(element.id)
                              ? "bg-orange-500 text-white"
                              : "bg-background-elevated text-foreground-secondary hover:bg-background-elevated/80"
                          )}
                        >
                          <span>{element.emoji}</span>
                          <span>{element.name}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* 配置检查 */}
                <div className="p-4 bg-background-tertiary rounded-xl space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    {isStrategyReady ? (
                      <CheckCircle2 className="w-4 h-4 text-accent-green" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-accent-yellow" />
                    )}
                    <span className={isStrategyReady ? 'text-accent-green' : 'text-accent-yellow'}>
                      Strategy Agent: {isStrategyReady ? '八大元素分析已就绪' : '需配置爆款元素'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    {isMemoryReady ? (
                      <CheckCircle2 className="w-4 h-4 text-accent-green" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-accent-yellow" />
                    )}
                    <span className={isMemoryReady ? 'text-accent-green' : 'text-accent-yellow'}>
                      Memory Agent: {isMemoryReady ? '素材库已就绪' : '需配置检索策略'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    {isGenerationReady ? (
                      <CheckCircle2 className="w-4 h-4 text-accent-green" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-accent-yellow" />
                    )}
                    <span className={isGenerationReady ? 'text-accent-green' : 'text-accent-yellow'}>
                      Generation Agent: {isGenerationReady ? '四大模板已配置' : '需配置脚本模板'}
                    </span>
                  </div>
                </div>

                {/* 生成按钮 */}
                <Button
                  className="w-full"
                  size="lg"
                  leftIcon={isGeneratingViral ? <Loader2 className="w-5 h-5 animate-spin" /> : <Flame className="w-5 h-5" />}
                  onClick={handleViralGenerate}
                  isLoading={isGeneratingViral}
                  disabled={
                    !viralText.trim() ||
                    isGeneratingViral ||
                    (
                      !(viralConfig.viralElements.includes('auto') || viralConfig.viralElements.includes('system_auto')) &&
                      viralConfig.viralElements.length < 2
                    )
                  }
                >
                  {isGeneratingViral ? '工业化流水线加工中...' : '生成爆款原创'}
                </Button>

                {!(viralConfig.viralElements.includes('auto') || viralConfig.viralElements.includes('system_auto')) && viralConfig.viralElements.length < 2 && (
                  <p className="text-xs text-accent-yellow text-center">
                    请至少选择2个爆款元素，以确保内容的爆款潜力
                  </p>
                )}
              </div>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </CreatorLayout>
  );
}

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(' ');
}
