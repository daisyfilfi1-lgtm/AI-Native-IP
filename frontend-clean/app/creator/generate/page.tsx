'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { CreatorLayout } from '@/components/creator/CreatorLayout';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { creatorApi } from '@/lib/api/creator';
import type { GeneratedContent } from '@/types/creator';
import { 
  Sparkles, 
  CheckCircle2, 
  AlertCircle,
  Edit3,
  Save,
  RefreshCw,
  ArrowLeft,
  Copy,
  Send,
  Loader2,
  Check,
  FileText,
  Library,
  Clock,
  TrendingUp
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

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

function GeneratePageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  
  // 从URL获取参数：id(生成ID) 和 type(生成类型: topic/remix/original，兼容viral)
  const id = searchParams.get('id');
  const type = searchParams.get('type') as 'topic' | 'remix' | 'original' | 'viral' | null;
  const normalizedType = type === 'viral' ? 'original' : type;
  
  const [isGenerating, setIsGenerating] = useState(true);
  const [progress, setProgress] = useState(0);
  const [content, setContent] = useState<GeneratedContent | null>(null);
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [editedContent, setEditedContent] = useState<Record<string, string>>({});
  const [isPublishing, setIsPublishing] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      
      // 延迟显示结果，让用户看到动画
      setTimeout(() => {
        setProgress(100);
        setContent(data);
        setIsGenerating(false);
      }, 1500);
      
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
      // 跳转到内容库
      router.push('/creator/library');
    } catch (err) {
      setError('发布失败，请重试');
      setIsPublishing(false);
    }
  };

  const getComplianceStatus = () => {
    if (!content?.compliance) return { passed: false, label: '未知', color: 'gray' };
    const { compliance } = content;
    const allPassed = compliance.platformChecks.douyin === 'passed' && 
                      compliance.platformChecks.xiaohongshu === 'passed';
    return {
      passed: allPassed,
      label: allPassed ? '已通过' : '需修改',
      color: allPassed ? 'green' : 'yellow'
    };
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
    <CreatorLayout>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link 
          href="/creator/dashboard"
          className="p-2 rounded-lg hover:bg-background-tertiary transition-colors"
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
              : type === 'topic' ? '基于推荐选题生成' : type === 'remix' ? '基于竞品仿写' : '基于语音扩写'}
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
                已调用: {type === 'topic' ? 'Strategy → Memory → Generation → Compliance' : 
                         type === 'remix' ? 'Remix → Memory → Generation → Compliance' :
                         'ASR → Memory → Generation → Compliance'}
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
            className="grid grid-cols-1 lg:grid-cols-3 gap-6"
          >
            {/* Content Editor */}
            <div className="lg:col-span-2 space-y-4">
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

            {/* Sidebar */}
            <div className="space-y-4">
              {/* 爆款原创特殊展示 */}
              {normalizedType === 'original' && content.viralElements && (
                <Card>
                  <div className="p-4">
                    <h3 className="font-semibold text-foreground mb-3">🎯 八大爆款元素</h3>
                    <div className="flex flex-wrap gap-2">
                      {content.viralElements.map((element: string) => (
                        <Badge key={element} variant="primary" size="sm">
                          {element}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </Card>
              )}
              
              {normalizedType === 'original' && content.scriptTemplate && (
                <Card>
                  <div className="p-4">
                    <h3 className="font-semibold text-foreground mb-3">📝 脚本模板</h3>
                    <div className="text-sm text-foreground-secondary">
                      {content.scriptTemplate === 'opinion' && '说观点：钩子→论据→升华'}
                      {content.scriptTemplate === 'process' && '晒过程：展示→情绪→结果'}
                      {content.scriptTemplate === 'knowledge' && '教知识：问题→原因→解决'}
                      {content.scriptTemplate === 'story' && '讲故事：困境→转折→方法→结果'}
                    </div>
                  </div>
                </Card>
              )}
              {/* Compliance Check */}
              <Card>
                <div className="p-4">
                  <h3 className="font-semibold text-foreground mb-3">合规检查</h3>
                  <div className="space-y-3">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-foreground-secondary">原创度</span>
                        <span className={cn(
                          "text-sm font-medium",
                          (content.compliance?.originalityScore || 0) >= 75 ? "text-accent-green" : "text-accent-yellow"
                        )}>
                          {content.compliance?.originalityScore || 0}%
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-background-tertiary rounded-full overflow-hidden">
                        <div 
                          className={cn(
                            "h-full rounded-full",
                            (content.compliance?.originalityScore || 0) >= 75 ? "bg-accent-green" : "bg-accent-yellow"
                          )}
                          style={{ width: `${content.compliance?.originalityScore || 0}%` }}
                        />
                      </div>
                    </div>
                    
                    <div className="flex items-center justify-between pt-2">
                      <span className="text-sm text-foreground-secondary">敏感词检测</span>
                      {content.compliance?.sensitiveWords && content.compliance.sensitiveWords.length > 0 ? (
                        <Badge variant="danger" size="sm">{content.compliance.sensitiveWords.length}个未通过</Badge>
                      ) : (
                        <Badge variant="success" size="sm">已通过</Badge>
                      )}
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-sm text-foreground-secondary">抖音平台</span>
                      <Badge 
                        variant={content.compliance?.platformChecks.douyin === 'passed' ? 'success' : 'warning'} 
                        size="sm"
                      >
                        {content.compliance?.platformChecks.douyin === 'passed' ? '通过' : '需修改'}
                      </Badge>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-sm text-foreground-secondary">小红书平台</span>
                      <Badge 
                        variant={content.compliance?.platformChecks.xiaohongshu === 'passed' ? 'success' : 'warning'} 
                        size="sm"
                      >
                        {content.compliance?.platformChecks.xiaohongshu === 'passed' ? '通过' : '需修改'}
                      </Badge>
                    </div>

                    <div className="pt-2 border-t border-border">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-foreground">整体状态</span>
                        <Badge 
                          variant={getComplianceStatus().passed ? 'success' : 'warning'} 
                          size="sm"
                        >
                          {getComplianceStatus().label}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Agent Chain Info */}
              <Card>
                <div className="p-4">
                  <h3 className="font-semibold text-foreground mb-3">Agent调用链</h3>
                  <div className="space-y-2">
                    {(content.agentChain || []).map((agent, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-sm">
                        <div className="w-5 h-5 rounded-full bg-accent-green/20 text-accent-green flex items-center justify-center text-xs font-medium">
                          {idx + 1}
                        </div>
                        <span className="text-foreground-secondary">{agent} Agent</span>
                        <CheckCircle2 className="w-3 h-3 text-accent-green ml-auto" />
                      </div>
                    ))}
                  </div>
                </div>
              </Card>

              {/* 黄金发布时间建议 */}
              <Card>
                <div className="p-4">
                  <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
                    <Clock className="w-4 h-4 text-primary-400" />
                    黄金发布时间
                  </h3>
                  <div className="p-3 rounded-xl bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20 mb-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-lg">💼</span>
                      <span className="font-medium text-foreground">职场类内容</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {[
                        { time: '8:00-9:00', label: '早高峰' },
                        { time: '12:00-13:00', label: '午休' },
                        { time: '20:00-22:00', label: '晚间' }
                      ].map((slot) => (
                        <button
                          key={slot.time}
                          className="px-3 py-1.5 rounded-lg bg-background-elevated hover:bg-primary-500/20 border border-border hover:border-primary-500/50 transition-all text-sm"
                        >
                          <span className="text-foreground">{slot.time}</span>
                          <span className="text-foreground-tertiary text-xs ml-1">{slot.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                  <p className="text-xs text-foreground-tertiary">
                    选择合适的发布时间可提升30%+的初始流量，建议提前5分钟发布
                  </p>
                </div>
              </Card>

              {/* Tips */}
              <Card>
                <div className="p-4">
                  <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-accent-yellow" />
                    数据优化建议
                  </h3>
                  <ul className="space-y-3 text-sm text-foreground-secondary">
                    <li className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan mt-1.5 flex-shrink-0" />
                      <span>
                        <strong className="text-foreground">完播率优化：</strong>
                        前3秒加入具体数字或争议观点，可提升20%完播率
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-accent-pink mt-1.5 flex-shrink-0" />
                      <span>
                        <strong className="text-foreground">点赞率优化：</strong>
                        在内容中段增加价值密度，每15秒一个信息点
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-accent-yellow mt-1.5 flex-shrink-0" />
                      <span>
                        <strong className="text-foreground">评论率优化：</strong>
                        CTA部分增加争议性话题或提问，引导互动
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-accent-green mt-1.5 flex-shrink-0" />
                      <span>
                        <strong className="text-foreground">转粉率优化：</strong>
                        结尾强化人设记忆点，使用固定slogan或视觉符号
                      </span>
                    </li>
                  </ul>
                </div>
              </Card>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </CreatorLayout>
  );
}

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(' ');
}

export default function CreatorGeneratePage() {
  return (
    <Suspense fallback={
      <CreatorLayout>
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </CreatorLayout>
    }>
      <GeneratePageContent />
    </Suspense>
  );
}
