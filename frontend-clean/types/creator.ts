// 创作者工作台类型定义
// 对应文档：场景-Agent-配置关联表

// ===== 样式类型 =====
export type StyleType = 'angry' | 'calm' | 'humor';

// ===== 仿写推荐（TikHub 低粉榜 + 关键词 / 小红书话题）=====
export interface RemixRecommendationItem {
  url: string;
  title: string;
  platform: 'douyin' | 'xiaohongshu';
  reason: string;
}

// ===== 选题卡片 =====
// 对应Agent：Strategy Agent输出
export interface TopicCard {
  id: string;
  title: string;                    // IP改写后的标题
  score: number;                    // Strategy Agent: 四维评分结果
  estimatedViews: string;           // Analytics Agent: 播放量预测
  estimatedCompletion: number;      // Analytics Agent: 完播率预测
  tags: string[];
  reason: string;                   // 匹配原因说明（来自Memory Agent素材匹配）
  agentChain?: string[];            // 涉及的Agent链
  
  // IP 2.0新增：原标题和原链接
  originalTitle?: string;           // 原始热点标题（TIKHUB数据源）
  sourceUrl?: string;               // 原链接（可点击跳转）
  contentCategory?: string;         // 内容矩阵分类（money/emotion/skill/life）
  filterMethod?: string;            // 匹配方式（keyword/semantic/ip_adapted）
  
  // Strategy Agent配置相关
  source?: string;                  // 来源竞品ID
  matchScore?: number;              // 团队素材匹配分（Memory Agent）
}

// ===== 生成内容 =====
// 对应Agent：Generation Agent输出 → Compliance Agent审核
export interface GeneratedContent {
  id: string;
  title: string;
  
  // 4段结构（Generation Agent分段生成）
  hook: string;                     // 钩子（黄金3秒）
  story: string;                    // 故事/案例
  opinion: string;                  // 观点/干货
  cta: string;                      // 行动号召
  
  // 风格配置（来自Generation Agent配置）
  style: StyleType;
  catchphrases?: string[];          // 检测到的口头禅
  
  // 溯源信息（Memory Agent提供）
  sourceTracing: SourceTrace[];
  
  // 合规检查（Compliance Agent输出）
  compliance: ComplianceResult;
  
  // Agent调用链
  agentChain: string[];
  
  // 爆款原创相关 (Viral Original)
  viralElements?: string[];         // 选中的爆款元素
  scriptTemplate?: string;          // 脚本模板ID
  customScriptHint?: string;        // 自定义模板时的结构说明（可选）

  // 元数据
  createdAt?: string;
  updatedAt?: string;
}

// ===== 素材溯源 =====
export interface SourceTrace {
  section: 'hook' | 'story' | 'opinion' | 'cta';
  sourceId: string;                 // 素材库中的ID
  sourceType?: 'story' | 'cognition' | 'scene' | 'remix';
  matchScore: number;               // 匹配度分数
  preview?: string;                 // 素材预览
}

// ===== 合规检查结果 =====
// 对应Agent：Compliance Agent输出
export interface ComplianceResult {
  originalityScore: number;         // 原创度分数（需>75%）
  sensitiveWords: SensitiveWord[];  // 检测到的敏感词
  platformChecks: {
    douyin: 'passed' | 'warning' | 'rejected';
    xiaohongshu: 'passed' | 'warning' | 'rejected';
  };
  suggestions?: string[];           // 修改建议
}

export interface SensitiveWord {
  word: string;
  level: 'red' | 'yellow' | 'blue'; // 三级敏感词
  position: string;                 // 出现位置
  suggestion: string;               // 替换建议
}

// ===== 内容库项目 =====
export interface LibraryItem {
  id: string;
  title: string;
  content: string;
  status: 'pending' | 'published' | 'viral' | 'draft';
  platforms?: string[];
  metrics?: {
    views: number;
    likes: number;
    comments: number;
    completionRate?: number;
  };
  createdAt: string;
  publishedAt?: string;
  
  // Agent相关
  generationSource?: 'topic' | 'remix' | 'voice' | 'original' | 'viral';
  sourceTopicId?: string;
  sourceUrl?: string;               // remix来源
  agentChain?: string[];
}

// ===== 数据分析指标 =====
// 对应Agent：Analytics Agent提供
export interface AnalyticsMetrics {
  // 核心指标
  published: number;                // 本周发布数
  viral: number;                    // 本周爆款数（>10万播放）
  leads: number;                    // 本周引流数
  
  // 效率指标（Analytics Agent计算）
  viralRate: number;                // 爆款率
  completionRate: number;           // 平均完播率
  engagementRate: number;           // 互动率
  
  // AI优化建议
  suggestions?: AIRecommendation[];
}

export interface AIRecommendation {
  id: string;
  type: 'hook' | 'timing' | 'topic' | 'style';
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  action?: string;
}

// ===== Agent配置类型（前端展示用） =====
export interface AgentConfig {
  // Strategy Agent配置
  strategy?: {
    competitorList: string[];       // 监控竞品列表
    scoreWeights: {
      traffic: number;              // 流量潜力权重
      monetization: number;         // 变现潜力权重
      fit: number;                  // 契合度权重
      cost: number;                 // 制作成本权重
    };
    blacklist: string[];            // 选题黑名单
  };
  
  // Memory Agent配置
  memory?: {
    tagSystem: {
      emotion: string[];
      scene: string[];
      cognition: string[];
    };
    retrievalStrategy: 'vector' | 'keyword' | 'hybrid';
    usageLimits: {
      story: number;
      cognition: number;
      scene: number;
    };
  };
  
  // Remix Agent配置
  remix?: {
    deconstructionRules: {
      hook: string[];
      emotion: string[];
      argument: string[];
      cta: string[];
    };
    originalityThreshold: {
      text: number;                 // 文本相似度阈值
      structure: number;            // 结构相似度阈值
    };
    hybridStrategy: 'full' | 'partial' | 'light';
  };
  
  // Generation Agent配置
  generation?: {
    styleTrainingSet: string[];     // S级文本ID列表（50篇）
    catchphrases: string[];         // 口头禅列表
    tabooWords: string[];           // 禁忌词列表
    sentenceLength: 'short' | 'medium' | 'long';
    emotionCurve: 'rising' | 'flat' | 'wavy';
  };
  
  // Compliance Agent配置
  compliance?: {
    sensitiveWords: {
      red: string[];
      yellow: string[];
      blue: string[];
    };
    platformRules: {
      douyin: PlatformRule;
      xiaohongshu: PlatformRule;
    };
    originalityThreshold: number;   // 原创度阈值（默认75%）
  };
}

export interface PlatformRule {
  maxLength: number;
  forbiddenWords: string[];
  contentGuidelines: string[];
}

// ===== API请求/响应类型 =====
export interface GenerateRequest {
  source: 'topic' | 'remix' | 'voice' | 'original' | 'viral';
  topicId?: string;
  remixUrl?: string;
  voiceText?: string;
  style: StyleType;
  options?: {
    strictCompliance?: boolean;     // 是否严格合规（默认true）
    useMemory?: boolean;            // 是否使用素材库（默认true）
  };
}

export interface GenerateResponse {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  currentAgent?: string;            // 当前正在执行的Agent
  estimatedTime?: number;           // 预估剩余时间（秒）
  error?: string;
}

// ===== 爆款原创配置 =====
// 对应工业化爆款生产流水线

// 八大爆款元素
export const VIRAL_ELEMENTS = [
  { id: 'cost', name: '成本', emoji: '💰', desc: '低成本/高成本' },
  { id: 'crowd', name: '人群', emoji: '👥', desc: '细分/特定人群' },
  { id: 'weird', name: '奇葩', emoji: '🤪', desc: '反常/猎奇' },
  { id: 'worst', name: '最差', emoji: '⛔', desc: '避坑/负面' },
  { id: 'contrast', name: '反差', emoji: '🔄', desc: '前后对比' },
  { id: 'nostalgia', name: '怀旧', emoji: '📷', desc: '情感共鸣' },
  { id: 'hormone', name: '荷尔蒙', emoji: '💖', desc: '颜值/情感' },
  { id: 'top', name: '头牌', emoji: '👑', desc: '第一/权威' },
] as const;

export type ViralElementId = typeof VIRAL_ELEMENTS[number]['id'];

// 黄金脚本模板（四大固定结构 + 自定义）
export const SCRIPT_TEMPLATES = [
  {
    id: 'opinion',
    name: '说观点',
    desc: '吸真粉/高互动',
    structure: ['钩子(3秒)', '论据(30秒)', '升华(5秒)'],
    keywords: ['我认为', '真相是', '揭秘'],
    bestFor: '建立专业人设，引发评论区讨论'
  },
  {
    id: 'process',
    name: '晒过程',
    desc: '强转化/近变现',
    structure: ['过程展示', '情绪铺垫', '结果呈现'],
    contentTypes: ['服务全流程', '产品测评', '任务挑战', '事件体验'],
    hookTechniques: ['反常识开头', '进度条预告', '身份悬念'],
    bestFor: '展示服务/产品交付过程，建立信任促成交'
  },
  {
    id: 'knowledge',
    name: '教知识',
    desc: '精准粉/高客单',
    structure: ['问题呈现', '原因分析', '解决步骤', '总结强调'],
    topicMethods: ['解题型', '案例型', '推荐型', '揭秘型', '颠覆型'],
    bestFor: '知识付费引流，筛选高意向用户'
  },
  {
    id: 'story',
    name: '讲故事',
    desc: '立人设/高信任',
    structure: ['困境(共情)', '转折(希望)', '方法(价值)', '结果(证明)'],
    prototypes: ['小有成就型', '平凡英雄型', '重新成功型'],
    bestFor: '高客单产品成交前，建立深度情感连接'
  },
  {
    id: 'custom',
    name: '自定义',
    desc: '按你的结构/节奏',
    structure: ['自选分段与时长'],
    bestFor: '有明确镜头表或口播提纲时使用'
  }
] as const;

export type ScriptTemplateId = typeof SCRIPT_TEMPLATES[number]['id'];

// 情感曲线模板
export const EMOTION_CURVES = [
  {
    id: 'angerHope',
    name: '愤怒-希望型',
    curve: ['痛点激怒(20%)', '情绪共鸣(30%)', '解决方案(40%)', '行动号召(10%)'],
    bestFor: '解决方案类内容'
  },
  {
    id: 'curiosityShock',
    name: '好奇-震惊型',
    curve: ['悬念设置(25%)', '逐步揭秘(35%)', '震惊事实(30%)', '引导互动(10%)'],
    bestFor: '揭秘类内容'
  },
  {
    id: 'problemSolution',
    name: '问题-解决型',
    curve: ['问题呈现(20%)', '原因分析(30%)', '解决步骤(40%)', '总结强调(10%)'],
    bestFor: '干货教程类内容'
  },
  {
    id: 'empathyInspire',
    name: '共情-励志型',
    curve: ['困境共情(25%)', '转折希望(25%)', '方法价值(35%)', '结果证明(15%)'],
    bestFor: '个人故事类内容'
  }
] as const;

export type EmotionCurveId = typeof EMOTION_CURVES[number]['id'];

// 选题评分卡（工业化标准）
export interface TopicScoreCard {
  targetAccuracy: number;    // 目标人群精准度 (0-2分)
  painIntensity: number;     // 痛点强度 (0-2分)
  viralElements: number;     // 爆款元素数量 (每个+1分，最高3分)
  productionCost: number;    // 制作难度 (-1至1分)
  monetizationFit: number;   // 变现关联度 (0-2分)
  totalScore: number;        // 总分 (≥7分才执行)
}

// 爆款原创请求参数
export interface ViralOriginalRequest {
  input: string;                    // 用户输入内容
  inputMode: 'text' | 'voice' | 'file';  // 输入方式
  scriptTemplate: ScriptTemplateId; // 脚本模板
  viralElements: ViralElementId[];  // 选中的爆款元素
  targetDuration: number;           // 目标时长（秒）
  style: StyleType;                 // 风格
  customScriptHint?: string;        // 选「自定义」时的结构说明（可选）
}

// 工业化流水线进度
export interface ViralPipelineProgress {
  step: number;
  totalSteps: number;
  stepName: string;
  description: string;
  percentage: number;
}

// ===== 工作台场景 =====
export type CreatorScenario = 'recommended' | 'remix' | 'viral';

export interface ScenarioConfig {
  id: CreatorScenario;
  name: string;
  description: string;
  agentChain: string[];             // 涉及的Agent链
  configRequired: string[];         // 需要配置的Agent
  icon: string;
}

export const SCENARIO_CONFIG: ScenarioConfig[] = [
  {
    id: 'recommended',
    name: '推荐选题',
    description: 'Strategy Agent智能推荐 + Memory Agent素材匹配',
    agentChain: ['Strategy', 'Memory', 'Analytics', 'Generation', 'Compliance'],
    configRequired: ['strategy', 'memory', 'generation', 'compliance'],
    icon: 'Sparkles'
  },
  {
    id: 'remix',
    name: '仿写爆款',
    description: 'Remix Agent结构仿写 + Memory Agent素材替换',
    agentChain: ['Remix', 'Memory', 'Generation', 'Compliance'],
    configRequired: ['remix', 'memory', 'generation', 'compliance'],
    icon: 'RefreshCw'
  },
  {
    id: 'viral',
    name: '爆款原创',
    description: '工业化流水线：八大元素 + 四大模板 + 七步精加工',
    agentChain: ['Strategy', 'Memory', 'Remix', 'Generation', 'Compliance'],
    configRequired: ['strategy', 'memory', 'remix', 'generation', 'compliance'],
    icon: 'Flame'
  }
];
