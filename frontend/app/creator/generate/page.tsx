'use client';

import { useState, useEffect, useCallback, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { CreatorLayout } from '@/components/creator/CreatorLayout';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { creatorApi } from '@/lib/api/creator';
import type { GeneratedContent, RefineHistoryEntry } from '@/types/creator';
import { 
  Sparkles, 
  CheckCircle2, 
  AlertCircle,
  Edit3,
  ArrowLeft,
  Copy,
  Send,
  Loader2,
  Check,
  FileText,
  GraduationCap,
  MessageCircle,
  ChevronDown
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCreatorIp } from '@/contexts/CreatorIpContext';

interface SectionConfig {
  title: string;
  color: string;
  description: string;
}

const sectionLabels: Record<string, SectionConfig> = {
  hook: { 
    title: '钩子', 
    color: 'text-accent-pink',
    description: '黄金3秒，抓住注意力'
  },
  story: { 
    title: '故事', 
    color: 'text-accent-cyan',
    description: '真实案例，引发共鸣'
  },
  opinion: { 
    title: '观点', 
    color: 'text-primary-400',
    description: '核心干货，建立专业'
  },
  cta: { 
    title: '行动指令', 
    color: 'text-accent-green',
    description: '引导互动，促进转化'
  },
};

type RefineChatBubble = { id: string; role: 'user' | 'assistant'; content: string };

function buildRefineChatMessages(history: RefineHistoryEntry[] | undefined): RefineChatBubble[] {
  if (!history?.length) return [];
  const out: RefineChatBubble[] = [];
  let n = 0;
  for (const h of history) {
    if (h.type && h.type !== 'refine') continue;
    const u = (h.user_feedback || '').trim();
    if (!u) continue;
    out.push({ id: `u-${n}`, role: 'user', content: u });
    n += 1;
    const a = (h.assistant_reply || '').trim();
    if (a) {
      out.push({ id: `a-${n}`, role: 'assistant', content: a });
      n += 1;
    }
  }
  return out;
}

function GeneratePageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { ipId } = useCreatorIp();
  
  // 从URL获取参数：id(生成ID) 和 type(生成类型: topic/remix/original，兼容viral)
  const id = searchParams.get('id');
  const type = searchParams.get('type') as 'topic' | 'remix' | 'original' | 'viral' | null;
  const normalizedType = type === 'viral' ? 'original' : type;
  const fromLibrary = searchParams.get('from') === 'library';
  
  const [isGenerating, setIsGenerating] = useState(true);
  const [progress, setProgress] = useState(0);
  const [content, setContent] = useState<GeneratedContent | null>(null);
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [editedContent, setEditedContent] = useState<Record<string, string>>({});
  const [isPublishing, setIsPublishing] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /** 对话改稿：与 Gemini 类似的多轮气泡（来自 refine_history） */
  const [refineChatMessages, setRefineChatMessages] = useState<RefineChatBubble[]>([]);
  const [refineInput, setRefineInput] = useState('');
  const [refineLoading, setRefineLoading] = useState(false);
  const refineChatAnchorRef = useRef<HTMLDivElement>(null);
  const refineChatScrollRef = useRef<HTMLDivElement>(null);
  const refineInputRef = useRef<HTMLTextAreaElement>(null);
  /** 满意后总结学习 */
  const [learningNote, setLearningNote] = useState('');
  const [learningLoading, setLearningLoading] = useState(false);
  const [styleLearnings, setStyleLearnings] = useState<Array<{ text: string }>>([]);
  const [learningToast, setLearningToast] = useState<string | null>(null);
  /** 改稿/总结失败时仅在侧栏提示，避免整页「出错了」 */
  const [refinePanelError, setRefinePanelError] = useState<string | null>(null);

  useEffect(() => {
    const el = refineChatScrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [refineChatMessages, refineLoading]);

  // 加载生成内容
  useEffect(() => {
    if (id) {
      loadContent();
    } else {
      // 如果没有ID，显示错误
      setError('无效的生成请求');
      setIsGenerating(false);
    }
  }, [id]);

  const refreshLearnings = useCallback(() => {
    if (!ipId) return;
    void creatorApi
      .getStyleLearnings(ipId)
      .then((r) => setStyleLearnings(r.items))
      .catch(() => setStyleLearnings([]));
  }, [ipId]);

  useEffect(() => {
    refreshLearnings();
  }, [refreshLearnings]);

  // 生成动画
  useEffect(() => {
    if (isGenerating && progress < 100) {
      const interval = setInterval(() => {
        setProgress(prev => {
          const increment = Math.random() * 15 + 5; // 5-20%的增量
          const newProgress = Math.min(prev + increment, 95);
          if (newProgress >= 95) {
            clearInterval(interval);
          }
          return newProgress;
        });
      }, 300);
      return () => clearInterval(interval);
    }
  }, [isGenerating, progress]);

  const loadContent = async () => {
    try {
      setIsGenerating(true);
      setProgress(0);
      setError(null);
      
      // 调用API获取生成内容
      const data = await creatorApi.getGeneratedContent(id!);
      const quickView = searchParams.get('from') === 'library';

      const apply = (d: GeneratedContent) => {
        setContent(d);
        setRefineChatMessages(buildRefineChatMessages(d.refine_history));
      };

      if (quickView) {
        setProgress(100);
        apply(data);
        setIsGenerating(false);
      } else {
        setTimeout(() => {
          setProgress(100);
          apply(data);
          setIsGenerating(false);
        }, 1500);
      }

    } catch (err) {
      console.error('Failed to load content:', err);
      setError('生成内容加载失败，请重试');
      setIsGenerating(false);
    }
  };

  const getSectionContent = (key: string): string => {
    if (!content) return '';
    switch (key) {
      case 'hook': return content.hook;
      case 'story': return content.story;
      case 'opinion': return content.opinion;
      case 'cta': return content.cta;
      default: return '';
    }
  };

  const getSectionSource = (key: string): string | undefined => {
    if (!content?.sourceTracing) return undefined;
    const trace = content.sourceTracing.find(t => t.section === key);
    return trace ? `素材_${trace.sourceId} (${trace.matchScore}%)` : undefined;
  };

  const handleEdit = (sectionKey: string) => {
    setEditingSection(sectionKey);
    setEditedContent(prev => ({ ...prev, [sectionKey]: getSectionContent(sectionKey) }));
  };

  const handleSaveEdit = (sectionKey: string) => {
    if (content) {
      const newContent = editedContent[sectionKey] || getSectionContent(sectionKey);
      setContent({
        ...content,
        [sectionKey]: newContent
      });
    }
    setEditingSection(null);
  };

  const handleCopy = () => {
    if (!content) return;
    const fullText = [content.hook, content.story, content.opinion, content.cta].join('\n\n');
    navigator.clipboard.writeText(fullText);
    // 显示复制成功提示
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-20 left-1/2 -translate-x-1/2 bg-accent-green text-white px-4 py-2 rounded-lg shadow-lg z-50';
    toast.textContent = '已复制到剪贴板';
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2000);
  };

  const handleSaveDraft = () => {
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);
  };

  const handlePublish = async () => {
    setIsPublishing(true);
    try {
      await creatorApi.publishContent(content?.id || '', ['douyin']);
      router.push('/creator/library');
    } catch (err) {
      setError('发布失败，请重试');
      setIsPublishing(false);
    }
  };

  const handleRefineSend = async () => {
    const text = refineInput.trim();
    if (!id || !ipId || !text || !content) return;
    setRefineLoading(true);
    setRefinePanelError(null);
    try {
      await creatorApi.refineDraft({
        draft_id: id,
        ip_id: ipId,
        user_feedback: text,
        hook: content.hook,
        story: content.story,
        opinion: content.opinion,
        cta: content.cta,
      });
      setRefineInput('');
      await loadContent();
    } catch (err) {
      setRefinePanelError(
        err instanceof Error ? err.message : '按反馈改写失败，请稍后重试'
      );
    } finally {
      setRefineLoading(false);
    }
  };

  const handleRecordLearning = async () => {
    if (!id || !ipId) return;
    setLearningLoading(true);
    setRefinePanelError(null);
    try {
      const r = await creatorApi.recordIterationLearning({
        draft_id: id,
        ip_id: ipId,
        user_note: learningNote.trim() || undefined,
      });
      setLearningNote('');
      setLearningToast(`已纳入 ${r.added} 条学习要点，后续生成将自动参考`);
      refreshLearnings();
      setTimeout(() => setLearningToast(null), 5000);
    } catch (err) {
      setRefinePanelError(
        err instanceof Error ? err.message : '总结学习失败，请稍后重试'
      );
    } finally {
      setLearningLoading(false);
    }
  };

  if (error) {
    return (
      <CreatorLayout>
        <div className="flex flex-col items-center justify-center py-20">
          <AlertCircle className="w-16 h-16 text-accent-red mb-4" />
          <h2 className="text-xl font-semibold text-foreground mb-2">出错了</h2>
          <p className="text-foreground-secondary mb-6">{error}</p>
          <div className="flex gap-3">
            <Link href="/creator/dashboard">
              <Button variant="secondary">返回工作台</Button>
            </Link>
            <Button onClick={() => loadContent()}>重新加载</Button>
          </div>
        </div>
      </CreatorLayout>
    );
  }

  return (
    <>
      <CreatorLayout>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link 
          href={fromLibrary ? '/creator/library' : '/creator/dashboard'}
          className="p-2 rounded-lg hover:bg-background-tertiary transition-colors"
          aria-label={fromLibrary ? '返回内容库' : '返回创作台'}
        >
          <ArrowLeft className="w-5 h-5 text-foreground-secondary" />
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-foreground">
            {isGenerating ? 'AI创作中...' : content?.title || '魔法生成'}
          </h1>
          <p className="text-sm text-foreground-secondary">
            {isGenerating 
              ? '正在调用Agent链为你生成内容...' 
              : type === 'topic'
                ? '基于推荐选题生成'
                : type === 'remix'
                  ? '基于竞品仿写'
                  : type === 'viral'
                    ? '爆款原创'
                    : '基于语音扩写'}
          </p>
        </div>
      </div>

      {/* Generation Animation or Content */}
      <AnimatePresence mode="wait">
        {isGenerating ? (
          <motion.div
            key="generating"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-20"
          >
            {/* Magic Animation */}
            <div className="relative mb-8">
              <motion.div
                className="w-24 h-24 rounded-full bg-gradient-to-br from-primary-500 to-accent-cyan flex items-center justify-center"
                animate={{
                  scale: [1, 1.1, 1],
                  rotate: [0, 5, -5, 0],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              >
                <Sparkles className="w-10 h-10 text-white" />
              </motion.div>
              
              {/* Orbiting particles */}
              {[...Array(3)].map((_, i) => (
                <motion.div
                  key={i}
                  className="absolute w-3 h-3 rounded-full bg-primary-400"
                  animate={{ rotate: 360 }}
                  transition={{
                    duration: 3 + i,
                    repeat: Infinity,
                    ease: "linear",
                  }}
                  style={{
                    top: '50%',
                    left: '50%',
                    marginLeft: -6,
                    marginTop: -6,
                    originX: 0,
                    originY: 0,
                    x: Math.cos((i * 120 * Math.PI) / 180) * 50,
                    y: Math.sin((i * 120 * Math.PI) / 180) * 50,
                  }}
                />
              ))}
            </div>

            {/* Agent Chain Status */}
            <div className="mb-6 space-y-2 text-center">
              <p className="text-lg font-semibold text-foreground">
                {progress < 30 ? 'Memory Agent 检索素材中...' : 
                 progress < 60 ? 'Generation Agent 生成文案中...' :
                 progress < 90 ? 'Compliance Agent 合规检查中...' : 
                 '即将完成...'}
              </p>
              <p className="text-sm text-foreground-secondary">
                已调用:{' '}
                {type === 'topic'
                  ? 'Strategy → Memory → Generation → Compliance'
                  : type === 'remix'
                    ? 'Remix → Memory → Generation → Compliance'
                    : type === 'viral'
                      ? 'Strategy → Memory → Generation → Compliance'
                      : 'ASR → Memory → Generation → Compliance'}
              </p>
            </div>

            {/* Progress Bar */}
            <div className="w-64 h-2 bg-background-tertiary rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-primary-500 to-accent-cyan"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
            <p className="text-xs text-foreground-tertiary mt-2">{Math.round(progress)}%</p>
          </motion.div>
        ) : content ? (
          <motion.div
            key="content"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="space-y-8"
          >
            {/* 正文区（与下方对话改稿同宽对齐） */}
            <div className="w-full max-w-3xl mx-auto px-2 sm:px-0 space-y-4">
              {Object.entries(sectionLabels).map(([key, config], index) => (
                <motion.div
                  key={key}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Card className="overflow-hidden">
                    <div className="p-4">
                      {/* Section Header */}
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className={cn("font-semibold", config.color)}>
                            {config.title}
                          </span>
                          <span className="text-xs text-foreground-tertiary">
                            {config.description}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          {getSectionSource(key) && (
                            <span className="text-xs text-foreground-tertiary bg-background-tertiary px-2 py-1 rounded">
                              来源: {getSectionSource(key)}
                            </span>
                          )}
                          {editingSection === key ? (
                            <Button
                              size="sm"
                              variant="ghost"
                              leftIcon={<CheckCircle2 className="w-4 h-4" />}
                              onClick={() => handleSaveEdit(key)}
                            >
                              保存
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="ghost"
                              leftIcon={<Edit3 className="w-4 h-4" />}
                              onClick={() => handleEdit(key)}
                            >
                              编辑
                            </Button>
                          )}
                        </div>
                      </div>

                      {/* Content */}
                      {editingSection === key ? (
                        <textarea
                          value={editedContent[key] || getSectionContent(key)}
                          onChange={(e) => setEditedContent(prev => ({ ...prev, [key]: e.target.value }))}
                          className="w-full min-h-[100px] p-3 bg-background-tertiary rounded-lg text-foreground resize-y focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                        />
                      ) : (
                        <p className="text-foreground leading-relaxed whitespace-pre-wrap">
                          {getSectionContent(key)}
                        </p>
                      )}
                    </div>
                  </Card>
                </motion.div>
              ))}

              {normalizedType === 'original' &&
                (Boolean(content.viralElements?.length) || Boolean(content.scriptTemplate)) && (
                  <details className="group rounded-xl border border-border bg-background-tertiary/25 overflow-hidden">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3 text-sm font-medium text-foreground hover:bg-background-tertiary/40 [&::-webkit-details-marker]:hidden">
                      <span>生成说明：爆款元素与脚本模板</span>
                      <ChevronDown className="h-4 w-4 shrink-0 text-foreground-tertiary transition-transform group-open:rotate-180" />
                    </summary>
                    <div className="space-y-4 border-t border-border px-4 pb-4 pt-3">
                      {content.viralElements && content.viralElements.length > 0 && (
                        <div>
                          <h4 className="mb-2 text-xs font-medium text-foreground-secondary">八大爆款元素</h4>
                          <div className="flex flex-wrap gap-2">
                            {content.viralElements.map((element: string) => (
                              <Badge key={element} variant="primary" size="sm">
                                {element}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                      {content.scriptTemplate && (
                        <div>
                          <h4 className="mb-2 text-xs font-medium text-foreground-secondary">脚本模板</h4>
                          <div className="text-sm text-foreground-secondary space-y-2">
                            {content.scriptTemplate === 'opinion' && '说观点：钩子→论据→升华'}
                            {content.scriptTemplate === 'process' && '晒过程：展示→情绪→结果'}
                            {content.scriptTemplate === 'knowledge' && '教知识：问题→原因→解决'}
                            {content.scriptTemplate === 'story' && '讲故事：困境→转折→方法→结果'}
                            {content.scriptTemplate === 'custom' && '自定义：按你的结构说明与时间轴组织全文'}
                            {content.scriptTemplate === 'custom' && content.customScriptHint?.trim() && (
                              <p className="text-xs text-foreground-tertiary whitespace-pre-wrap border-t border-border pt-2">
                                {content.customScriptHint.trim()}
                              </p>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </details>
                )}

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4">
                <Button
                  variant="secondary"
                  leftIcon={<Copy className="w-4 h-4" />}
                  onClick={handleCopy}
                >
                  复制文案
                </Button>
                <Button
                  variant="secondary"
                  leftIcon={isSaved ? <Check className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                  onClick={handleSaveDraft}
                >
                  {isSaved ? '已保存' : '保存草稿'}
                </Button>
                <Button
                  className="flex-1"
                  leftIcon={isPublishing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  onClick={handlePublish}
                  isLoading={isPublishing}
                >
                  {isPublishing ? '发布中...' : '发布内容'}
                </Button>
              </div>
            </div>

            {/* 发布区下方：仅对话改稿（全宽居中，避免挤在侧栏偏左） */}
            <div ref={refineChatAnchorRef} className="w-full flex justify-center px-2 sm:px-0">
              <Card className="w-full max-w-3xl border-border/80">
                <div className="p-4 sm:p-5">
                  <h3 className="font-semibold text-foreground mb-1 flex items-center gap-2">
                    <MessageCircle className="w-4 h-4 text-primary-400" />
                    对话改稿
                  </h3>
                  <p className="text-xs text-foreground-tertiary mb-3">
                    像和 Gemini 一样多轮说明：你写什么，模型就按你的意思改；上方正文会同步更新。满意后再用下方「总结学习」写入 IP 长期偏好。
                  </p>

                  {refinePanelError && (
                    <div
                      role="alert"
                      className="mb-3 rounded-lg border border-accent-red/40 bg-accent-red/10 px-3 py-2 text-xs text-foreground"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="whitespace-pre-wrap">{refinePanelError}</span>
                        <button
                          type="button"
                          className="shrink-0 text-foreground-tertiary hover:text-foreground"
                          onClick={() => setRefinePanelError(null)}
                          aria-label="关闭"
                        >
                          ×
                        </button>
                      </div>
                    </div>
                  )}

                  <div
                    ref={refineChatScrollRef}
                    className="mb-3 max-h-64 overflow-y-auto rounded-lg border border-border/80 bg-background-tertiary/50 p-2 space-y-2"
                  >
                    {refineChatMessages.length === 0 && !refineLoading && (
                      <p className="text-xs text-foreground-muted px-2 py-2">
                        在下方输入框直接说想怎么改，例如：「钩子先上数字」「故事换成我亲历的」「结尾别像广告」…
                      </p>
                    )}
                    {refineChatMessages.map((m) => (
                      <div
                        key={m.id}
                        className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[92%] rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap ${
                            m.role === 'user'
                              ? 'bg-primary-500/20 text-foreground border border-primary-500/30'
                              : 'bg-background-elevated text-foreground-secondary border border-border'
                          }`}
                        >
                          {m.content}
                        </div>
                      </div>
                    ))}
                    {refineLoading && (
                      <div className="flex justify-start">
                        <div className="rounded-2xl border border-border bg-background-elevated px-3 py-2 text-xs text-foreground-muted flex items-center gap-2">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          正在改稿…
                        </div>
                      </div>
                    )}
                  </div>

                  <textarea
                    ref={refineInputRef}
                    value={refineInput}
                    onChange={(e) => setRefineInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        void handleRefineSend();
                      }
                    }}
                    placeholder="说说想怎么改…（Enter 发送，Shift+Enter 换行）"
                    rows={3}
                    disabled={!ipId || refineLoading}
                    className="w-full rounded-lg border border-border bg-background-tertiary px-3 py-2 text-sm text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-primary-500/40 resize-y mb-2"
                  />
                  <Button
                    type="button"
                    className="w-full mb-4"
                    size="sm"
                    disabled={!ipId || !refineInput.trim() || refineLoading}
                    isLoading={refineLoading}
                    onClick={() => void handleRefineSend()}
                  >
                    发送并改稿
                  </Button>

                  <div className="border-t border-border pt-3">
                    <h4 className="text-sm font-medium text-foreground mb-1 flex items-center gap-2">
                      <GraduationCap className="w-4 h-4 text-accent-yellow" />
                      满意后：总结并纳入 IP 学习
                    </h4>
                    <textarea
                      value={learningNote}
                      onChange={(e) => setLearningNote(e.target.value)}
                      placeholder="可选：你认为这次最大的问题是什么"
                      rows={2}
                      disabled={!ipId || learningLoading}
                      className="w-full rounded-lg border border-border bg-background-tertiary px-3 py-2 text-xs text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-primary-500/40 resize-y mb-2"
                    />
                    <Button
                      type="button"
                      variant="secondary"
                      className="w-full"
                      size="sm"
                      disabled={!ipId || learningLoading}
                      isLoading={learningLoading}
                      onClick={() => void handleRecordLearning()}
                    >
                      总结学习并写入 IP
                    </Button>
                  </div>

                  {styleLearnings.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-border">
                      <p className="text-xs font-medium text-foreground-secondary mb-2">
                        已沉淀要点（已写入配置并同步 Memory 向量库，检索与生成会参考）
                      </p>
                      <ul className="space-y-2 max-h-44 overflow-y-auto text-xs text-foreground-tertiary">
                        {styleLearnings.map((item, idx) => (
                          <li key={idx} className="flex gap-2">
                            <span className="text-primary-400 shrink-0">•</span>
                            <span>{item.text}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </Card>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </CreatorLayout>

      {learningToast && (
        <div className="fixed bottom-6 left-1/2 z-[60] -translate-x-1/2 max-w-md rounded-xl border border-accent-green/30 bg-background-elevated px-4 py-3 text-sm text-foreground shadow-lg">
          {learningToast}
        </div>
      )}
    </>
  );
}

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(' ');
}

export default function CreatorGeneratePage() {
  return (
    <Suspense
      fallback={
        <CreatorLayout>
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
          </div>
        </CreatorLayout>
      }
    >
      <GeneratePageContent />
    </Suspense>
  );
}
