'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Progress } from '@/components/ui/Progress';
import { Badge } from '@/components/ui/Badge';
import { 
  MessageSquare, 
  Sparkles, 
  CheckCircle2, 
  ChevronRight,
  Bot,
  User,
  ArrowRight,
  Lightbulb,
  Save,
  RotateCcw
} from 'lucide-react';

// ===== 配置问题定义 =====
interface Question {
  id: string;
  agent: string;
  question: string;
  description?: string;
  type: 'text' | 'select' | 'multiselect' | 'number' | 'textarea' | 'confirm';
  options?: { value: string; label: string; description?: string }[];
  placeholder?: string;
  example?: string;
  tips?: string[];
}

const CONFIG_QUESTIONS: Question[] = [
  // === Strategy Agent 配置 ===
  {
    id: 'strategy_competitors',
    agent: 'Strategy',
    question: '你想重点关注哪些竞争对手或对标账号？',
    description: '我们会监控这些账号的爆款内容，为你推荐类似的优质选题',
    type: 'textarea',
    placeholder: '例如：\n@张三（商业认知类）\n@李四（创业故事类）\n@王五（私域运营类）',
    example: '@张三, @李四（可以填写3-5个你最欣赏的对标账号）',
    tips: ['选择和你定位相似的账号', '建议关注10-50万粉丝的账号，内容质量更高', '可以是抖音、视频号或小红书的账号']
  },
  {
    id: 'strategy_topics',
    agent: 'Strategy',
    question: '你的内容主要围绕哪些主题？',
    description: '这帮助我们更精准地筛选适合你的选题',
    type: 'multiselect',
    options: [
      { value: 'business', label: '商业认知', description: '商业模式、创业思维、商业案例' },
      { value: 'startup', label: '创业故事', description: '创业经历、踩坑分享、翻身案例' },
      { value: 'private_domain', label: '私域运营', description: '微信生态、社群运营、朋友圈营销' },
      { value: 'personal_growth', label: '个人成长', description: '认知提升、时间管理、学习方法' },
      { value: 'investment', label: '投资理财', description: '理财知识、投资案例、财富思维' },
      { value: 'industry', label: '行业洞察', description: '行业趋势、赛道分析、机会判断' },
    ]
  },
  {
    id: 'strategy_avoid',
    agent: 'Strategy',
    question: '有哪些话题是你明确不想碰的？',
    description: '我们会自动过滤掉这些选题',
    type: 'textarea',
    placeholder: '例如：政治敏感话题、争议性社会事件、虚假炫富...',
    example: '政治、宗教、医疗建议、虚假炫富',
    tips: ['这有助于保护你的账号安全', '也可以填写你个人不感兴趣的话题']
  },

  // === Memory Agent 配置 ===
  {
    id: 'memory_stories',
    agent: 'Memory',
    question: '你有哪些真实的故事或经历可以分享？',
    description: '这些素材会被AI用于生成更有真实感的内容',
    type: 'textarea',
    placeholder: '简要描述几个你的真实经历...',
    example: '2020年公司差点倒闭的经历；第一次月入10万的故事；被合伙人背叛的经历...',
    tips: ['不需要写得很详细，关键词即可', '可以是成功经历，也可以是失败教训', '这些素材不会被直接发布，只用于生成参考']
  },
  {
    id: 'memory_catchphrases',
    agent: 'Memory',
    question: '你有常说的口头禅或标志性语句吗？',
    description: 'AI会在内容中自然地使用这些表达，让你的内容更有个人特色',
    type: 'text',
    placeholder: '例如：记住，这一点很关键；我直接告诉你；别犹豫',
    example: '"记住这个核心点" / "我跟你讲" / "别绕弯子"',
    tips: ['3-5个即可', '不要太长，简短有力的更好']
  },

  // === Generation Agent 配置 ===
  {
    id: 'generation_style',
    agent: 'Generation',
    question: '你希望内容呈现什么样的风格？',
    description: '这决定了AI生成内容的语气和表达方式',
    type: 'select',
    options: [
      { value: 'angry', label: '🔥 直击痛点型', description: '语气犀利，直击问题核心，适合引发共鸣' },
      { value: 'calm', label: '😌 理性分析型', description: '逻辑清晰，数据支撑，适合建立专业形象' },
      { value: 'humor', label: '😄 轻松幽默型', description: '轻松有趣，寓教于乐，适合拉近距离' },
      { value: 'story', label: '📖 故事讲述型', description: '情感丰富，画面感强，适合引发共情' },
      { value: 'mentor', label: '👨‍🏫 导师教导型', description: '循循善诱，经验分享，适合建立权威' },
    ]
  },
  {
    id: 'generation_taboo',
    agent: 'Generation',
    question: '有哪些词或表达是你绝对不会用的？',
    description: 'AI会完全避免使用这些词汇',
    type: 'textarea',
    placeholder: '例如：割韭菜、智商税、绝对化用语...',
    example: '"保证赚钱" / "稳赚不赔" / 其他你觉得low的表达',
    tips: ['这有助于维护你的个人品牌形象', '也可以是你觉得过于营销的词汇']
  },

  // === Remix Agent 配置 ===
  {
    id: 'remix_level',
    agent: 'Remix',
    question: '仿写爆款时，你希望多大程度的创新？',
    description: '这决定了AI在仿写时是更保守还是更大胆',
    type: 'select',
    options: [
      { value: 'light', label: '轻度借鉴', description: '主要借鉴选题方向，内容完全原创，最安全' },
      { value: 'medium', label: '结构借鉴', description: '借鉴爆款结构（钩子-故事-观点-CTA），内容用自己的素材，推荐' },
      { value: 'deep', label: '深度重构', description: '借鉴表达方式，但用你自己的案例和观点，需要较强原创能力' },
    ]
  },

  // === Compliance Agent 配置 ===
  {
    id: 'compliance_strict',
    agent: 'Compliance',
    question: '合规检查的严格程度？',
    description: '更严格的检查会更安全，但可能会过滤掉一些边缘选题',
    type: 'select',
    options: [
      { value: 'strict', label: '严格模式', description: '宁可不过，也不冒险，适合新手' },
      { value: 'normal', label: '标准模式', description: '平衡安全性和创作自由度，推荐' },
      { value: 'loose', label: '宽松模式', description: '更多创作自由，但需要你有较强的自我审查能力' },
    ]
  },
];

// ===== 消息类型 =====
interface Message {
  id: string;
  type: 'bot' | 'user' | 'system';
  content: string;
  questionId?: string;
  options?: { value: string; label: string; description?: string }[];
  tips?: string[];
  example?: string;
}

// ===== 主组件 =====
export default function AgentOnboardingPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(-1);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [inputValue, setInputValue] = useState('');
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 初始化：显示欢迎消息
  useEffect(() => {
    setTimeout(() => {
      setMessages([
        {
          id: 'welcome',
          type: 'bot',
          content: '你好！我是你的AI配置助手 🤖\n\n我会通过几个简单的问题，帮你完成所有Agent的配置。大概需要3-5分钟。\n\n准备好了吗？',
        }
      ]);
      setCurrentQuestionIndex(0);
    }, 500);
  }, []);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 显示下一个问题
  const showNextQuestion = (index: number) => {
    if (index >= CONFIG_QUESTIONS.length) {
      // 所有问题完成
      setMessages(prev => [...prev, {
        id: 'complete',
        type: 'bot',
        content: '太棒了！所有配置都已完成 ✅\n\n我来总结一下你的配置：\n\n' + generateSummary(),
      }]);
      setIsComplete(true);
      return;
    }

    const q = CONFIG_QUESTIONS[index];
    setTimeout(() => {
      setMessages(prev => [...prev, {
        id: q.id,
        type: 'bot',
        content: q.question,
        questionId: q.id,
        options: q.options,
        tips: q.tips,
        example: q.example,
      }]);
      setCurrentQuestionIndex(index);
      setInputValue('');
      setSelectedOptions([]);
    }, 600);
  };

  // 生成配置摘要
  const generateSummary = () => {
    const summary = [];
    const competitorAnswer = answers['strategy_competitors'];
    if (competitorAnswer) {
      summary.push(`📊 监控了 ${competitorAnswer.split(/[@,，\n]/).filter(Boolean).length} 个对标账号`);
    }
    const topicAnswer = answers['strategy_topics'];
    if (topicAnswer) {
      summary.push(`🎯 选择了 ${topicAnswer.length} 个内容主题`);
    }
    const styleAnswer = answers['generation_style'];
    if (styleAnswer) {
      const styleMap: Record<string, string> = {
        angry: '🔥 直击痛点型',
        calm: '😌 理性分析型',
        humor: '😄 轻松幽默型',
        story: '📖 故事讲述型',
        mentor: '👨‍🏫 导师教导型',
      };
      summary.push(`✍️ 内容风格：${styleMap[styleAnswer] || styleAnswer}`);
    }
    const remixLevel = answers['remix_level'];
    if (remixLevel) {
      const levelMap: Record<string, string> = {
        light: '轻度借鉴',
        medium: '结构借鉴',
        deep: '深度重构',
      };
      summary.push(`🔄 仿写策略：${levelMap[remixLevel]}`);
    }
    return summary.join('\n');
  };

  // 处理用户回答
  const handleSubmit = () => {
    const q = CONFIG_QUESTIONS[currentQuestionIndex];
    let answer: any;

    if (q.type === 'multiselect') {
      if (selectedOptions.length === 0) return;
      answer = selectedOptions;
    } else if (q.type === 'select') {
      if (!inputValue) return;
      answer = inputValue;
    } else {
      if (!inputValue.trim()) return;
      answer = inputValue.trim();
    }

    // 保存答案
    setAnswers(prev => ({ ...prev, [q.id]: answer }));

    // 显示用户消息
    let displayAnswer = answer;
    if (Array.isArray(answer)) {
      displayAnswer = answer.map(v => q.options?.find(o => o.value === v)?.label || v).join('、');
    } else if (q.options) {
      displayAnswer = q.options.find(o => o.value === answer)?.label || answer;
    }

    setMessages(prev => [...prev, {
      id: `answer-${q.id}`,
      type: 'user',
      content: displayAnswer,
    }]);

    // 显示下一个问题
    showNextQuestion(currentQuestionIndex + 1);
  };

  // 跳过当前问题
  const handleSkip = () => {
    const q = CONFIG_QUESTIONS[currentQuestionIndex];
    setMessages(prev => [...prev, {
      id: `skip-${q.id}`,
      type: 'user',
      content: '跳过这个问题',
    }, {
      id: `skip-response-${q.id}`,
      type: 'bot',
      content: '好的，这个问题我们先跳过，你可以之后在设置里补充。',
    }]);
    showNextQuestion(currentQuestionIndex + 1);
  };

  // 保存配置
  const handleSave = async () => {
    setIsSaving(true);
    // 模拟保存
    await new Promise(resolve => setTimeout(resolve, 1500));
    setIsSaving(false);
    // 可以在这里跳转到其他页面
    window.location.href = '/agents';
  };

  // 重新开始
  const handleRestart = () => {
    setMessages([]);
    setCurrentQuestionIndex(-1);
    setAnswers({});
    setInputValue('');
    setSelectedOptions([]);
    setIsComplete(false);
    setTimeout(() => {
      setMessages([{
        id: 'welcome',
        type: 'bot',
        content: '你好！我是你的AI配置助手 🤖\n\n我会通过几个简单的问题，帮你完成所有Agent的配置。大概需要3-5分钟。\n\n准备好了吗？',
      }]);
      setCurrentQuestionIndex(0);
    }, 500);
  };

  // 当前问题
  const currentQuestion = CONFIG_QUESTIONS[currentQuestionIndex];
  const progress = ((currentQuestionIndex) / CONFIG_QUESTIONS.length) * 100;

  // 检查是否可以提交
  const canSubmit = () => {
    if (!currentQuestion) return false;
    if (currentQuestion.type === 'multiselect') {
      return selectedOptions.length > 0;
    }
    return inputValue.trim() !== '';
  };

  return (
    <MainLayout title="Agent配置引导">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-cyan flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-foreground">AI配置助手</h1>
              <p className="text-sm text-foreground-secondary">通过对话完成7-Agent配置</p>
            </div>
          </div>
          
          {/* Progress */}
          {!isComplete && (
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs text-foreground-secondary mb-2">
                <span>配置进度</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <Progress value={progress} size="sm" variant="gradient" />
            </div>
          )}
        </div>

        {/* Chat Area */}
        <Card className="min-h-[500px] flex flex-col">
          {/* Messages */}
          <div className="flex-1 p-4 space-y-4 overflow-y-auto max-h-[600px]">
            <AnimatePresence>
              {messages.map((msg, index) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn(
                    "flex gap-3",
                    msg.type === 'user' ? "flex-row-reverse" : ""
                  )}
                >
                  {/* Avatar */}
                  <div className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                    msg.type === 'bot' ? "bg-primary-500/10" : "bg-accent-cyan/10"
                  )}>
                    {msg.type === 'bot' ? (
                      <Bot className="w-4 h-4 text-primary-400" />
                    ) : (
                      <User className="w-4 h-4 text-accent-cyan" />
                    )}
                  </div>

                  {/* Message Content */}
                  <div className={cn(
                    "max-w-[80%] rounded-2xl p-4",
                    msg.type === 'bot' 
                      ? "bg-background-tertiary rounded-tl-sm" 
                      : "bg-primary-500 text-white rounded-tr-sm"
                  )}>
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    
                    {/* Tips */}
                    {msg.tips && msg.tips.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-border/50">
                        <div className="flex items-center gap-1 text-xs text-foreground-tertiary mb-2">
                          <Lightbulb className="w-3 h-3" />
                          <span>小贴士</span>
                        </div>
                        <ul className="space-y-1">
                          {msg.tips.map((tip, i) => (
                            <li key={i} className="text-xs text-foreground-secondary flex items-start gap-1">
                              <span className="text-primary-400 mt-0.5">•</span>
                              {tip}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Example */}
                    {msg.example && (
                      <div className="mt-3 pt-3 border-t border-border/50">
                        <p className="text-xs text-foreground-tertiary">
                          示例：{msg.example}
                        </p>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          {!isComplete && currentQuestion && (
            <div className="p-4 border-t border-border">
              {/* Multi-select Options */}
              {currentQuestion.type === 'multiselect' && currentQuestion.options && (
                <div className="mb-4 space-y-2">
                  {currentQuestion.options.map(option => (
                    <button
                      key={option.value}
                      onClick={() => {
                        setSelectedOptions(prev => 
                          prev.includes(option.value)
                            ? prev.filter(v => v !== option.value)
                            : [...prev, option.value]
                        );
                      }}
                      className={cn(
                        "w-full p-3 rounded-xl border text-left transition-all",
                        selectedOptions.includes(option.value)
                          ? "border-primary-500 bg-primary-500/10"
                          : "border-border hover:border-border-hover"
                      )}
                    >
                      <div className="flex items-start gap-3">
                        <div className={cn(
                          "w-5 h-5 rounded border flex items-center justify-center flex-shrink-0 mt-0.5",
                          selectedOptions.includes(option.value)
                            ? "bg-primary-500 border-primary-500"
                            : "border-foreground-tertiary"
                        )}>
                          {selectedOptions.includes(option.value) && (
                            <CheckCircle2 className="w-3 h-3 text-white" />
                          )}
                        </div>
                        <div>
                          <p className="font-medium text-foreground">{option.label}</p>
                          {option.description && (
                            <p className="text-xs text-foreground-secondary mt-0.5">{option.description}</p>
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Single-select Options */}
              {currentQuestion.type === 'select' && currentQuestion.options && (
                <div className="mb-4 space-y-2">
                  {currentQuestion.options.map(option => (
                    <button
                      key={option.value}
                      onClick={() => setInputValue(option.value)}
                      className={cn(
                        "w-full p-3 rounded-xl border text-left transition-all",
                        inputValue === option.value
                          ? "border-primary-500 bg-primary-500/10"
                          : "border-border hover:border-border-hover"
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          "w-4 h-4 rounded-full border flex-shrink-0",
                          inputValue === option.value
                            ? "border-4 border-primary-500"
                            : "border-foreground-tertiary"
                        )} />
                        <div className="flex-1">
                          <p className="font-medium text-foreground">{option.label}</p>
                          {option.description && (
                            <p className="text-xs text-foreground-secondary mt-0.5">{option.description}</p>
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Text/textarea Input */}
              {(currentQuestion.type === 'text' || currentQuestion.type === 'textarea') && (
                <div className="mb-4">
                  <textarea
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder={currentQuestion.placeholder}
                    rows={currentQuestion.type === 'textarea' ? 4 : 2}
                    className="w-full p-3 bg-background-tertiary border border-border rounded-xl text-foreground placeholder:text-foreground-muted resize-none focus:outline-none focus:border-primary-500/50"
                  />
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-3">
                <Button
                  className="flex-1"
                  leftIcon={<ArrowRight className="w-4 h-4" />}
                  onClick={handleSubmit}
                  disabled={!canSubmit()}
                >
                  {currentQuestionIndex === CONFIG_QUESTIONS.length - 1 ? '完成配置' : '下一个'}
                </Button>
                <Button
                  variant="ghost"
                  onClick={handleSkip}
                >
                  跳过
                </Button>
              </div>
            </div>
          )}

          {/* Complete Actions */}
          {isComplete && (
            <div className="p-4 border-t border-border space-y-3">
              <Button
                className="w-full"
                size="lg"
                leftIcon={isSaving ? undefined : <Save className="w-4 h-4" />}
                onClick={handleSave}
                isLoading={isSaving}
              >
                {isSaving ? '保存中...' : '保存配置'}
              </Button>
              <Button
                variant="secondary"
                className="w-full"
                leftIcon={<RotateCcw className="w-4 h-4" />}
                onClick={handleRestart}
              >
                重新配置
              </Button>
            </div>
          )}
        </Card>

        {/* Tips Card */}
        <Card className="mt-6">
          <div className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb className="w-4 h-4 text-accent-yellow" />
              <span className="font-medium text-foreground">为什么要这样配置？</span>
            </div>
            <ul className="space-y-2 text-sm text-foreground-secondary">
              <li className="flex items-start gap-2">
                <span className="text-primary-400">1.</span>
                对标账号帮助我们了解你的内容定位，为你推荐合适的选题
              </li>
              <li className="flex items-start gap-2">
                <span className="text-primary-400">2.</span>
                个人故事素材让AI生成的内容更有真实感和个人特色
              </li>
              <li className="flex items-start gap-2">
                <span className="text-primary-400">3.</span>
                风格偏好确保每次生成的内容都符合你的调性
              </li>
              <li className="flex items-start gap-2">
                <span className="text-primary-400">4.</span>
                所有配置都可以在设置中随时修改
              </li>
            </ul>
          </div>
        </Card>
      </div>
    </MainLayout>
  );
}

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(' ');
}
