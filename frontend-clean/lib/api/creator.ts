// 创作者工作台API
// 对应后台：7-Agent工作流系统

import {
  TopicCard,
  GeneratedContent,
  LibraryItem,
  AnalyticsMetrics,
  StyleType,
  RemixRecommendationItem,
} from '@/types/creator';
import { getApiOriginOrEmpty } from '@/lib/apiBaseUrl';
import { getStoredToken } from '@/lib/auth';

// ===== Agent配置状态类型 =====
export interface AgentStatus {
  status: 'ready' | 'configuring' | 'error';
  config: string[];
  lastUpdated?: string;
}

export interface AgentConfigStatus {
  // 场景一：推荐选题相关Agent
  strategy: AgentStatus;    // 策略Agent：评分权重、竞品监控
  memory: AgentStatus;      // 记忆Agent：标签体系、检索策略
  analytics: AgentStatus;   // 分析Agent：预测模型
  
  // 场景二：仿写爆款相关Agent
  remix: AgentStatus;       // 混剪Agent：解构规则、原创度
  
  // 场景三：爆款原创相关Agent（含语音输入能力）
  asr: AgentStatus;         // 语音识别：ASR服务状态
  
  // 通用生成Agent
  generation: AgentStatus;  // 生成Agent：风格训练、口头禅、禁忌词
  compliance: AgentStatus;  // 合规Agent：敏感词库、平台规则
}

// ===== 生成结果类型 =====
export interface GenerateResult {
  id: string;
  status: 'processing' | 'completed' | 'failed';
  progress?: number;
  estimatedTime?: number;
}

// ===== Mock数据 =====
const mockTopics: TopicCard[] = [
  {
    id: 'topic_001',
    title: '现金流断裂如何自救：从负债500万到3年翻身的真实案例',
    score: 4.85,
    estimatedViews: '50-80万',
    estimatedCompletion: 38,
    tags: ['现金流', '创业', '翻身'],
    reason: '故事_003素材匹配 + 现金流话题近期热度↑',
    agentChain: ['Strategy', 'Memory', 'Generation', 'Compliance']
  },
  {
    id: 'topic_002',
    title: '为什么90%的IP都在第一步做错了？',
    score: 4.72,
    estimatedViews: '30-50万',
    estimatedCompletion: 35,
    tags: ['IP定位', '认知'],
    reason: '竞对@张三近期爆款结构 + 高变现潜力',
    agentChain: ['Strategy', 'Memory', 'Generation', 'Compliance']
  },
  {
    id: 'topic_003',
    title: '月入3万的私域运营，朋友圈应该怎么发？',
    score: 4.65,
    estimatedViews: '25-40万',
    estimatedCompletion: 42,
    tags: ['私域', '变现'],
    reason: '团队专属素材库匹配 + 低竞争度蓝海',
    agentChain: ['Strategy', 'Memory', 'Generation', 'Compliance']
  }
];

const mockLibraryItems: LibraryItem[] = [
  {
    id: 'content_001',
    title: '现金流断裂如何自救：从负债500万到3年翻身的真实案例',
    content: '',
    status: 'published',
    platforms: ['douyin'],
    metrics: {
      views: 85600,
      likes: 4200,
      comments: 380,
      completionRate: 38.5
    },
    createdAt: '2026-03-15T10:30:00Z',
    publishedAt: '2026-03-15T12:00:00Z',
    generationSource: 'topic',
    sourceTopicId: 'topic_001',
    agentChain: ['Strategy', 'Memory', 'Generation', 'Compliance']
  },
  {
    id: 'content_002',
    title: '为什么90%的IP都在第一步做错了？',
    content: '',
    status: 'viral',
    platforms: ['douyin', 'xiaohongshu'],
    metrics: {
      views: 125000,
      likes: 8900,
      comments: 1200,
      completionRate: 42.1
    },
    createdAt: '2026-03-10T09:00:00Z',
    publishedAt: '2026-03-10T11:00:00Z',
    generationSource: 'topic',
    sourceTopicId: 'topic_002',
    agentChain: ['Strategy', 'Memory', 'Generation', 'Compliance']
  },
  {
    id: 'content_003',
    title: '月入3万的私域运营，朋友圈应该怎么发？',
    content: '',
    status: 'pending',
    platforms: [],
    createdAt: '2026-03-17T14:00:00Z',
    generationSource: 'topic',
    sourceTopicId: 'topic_003',
    agentChain: ['Strategy', 'Memory', 'Generation', 'Compliance']
  },
  {
    id: 'content_004',
    title: '2024年最适合普通人的副业TOP5',
    content: '',
    status: 'draft',
    platforms: [],
    createdAt: '2026-03-17T16:30:00Z',
    generationSource: 'remix',
    agentChain: ['Remix', 'Memory', 'Generation', 'Compliance']
  },
  {
    id: 'content_005',
    title: '一个30岁男人的真实创业故事',
    content: '',
    status: 'published',
    platforms: ['xiaohongshu'],
    metrics: {
      views: 32000,
      likes: 2100,
      comments: 156,
      completionRate: 35.2
    },
    createdAt: '2026-03-12T08:00:00Z',
    publishedAt: '2026-03-12T10:00:00Z',
    generationSource: 'original',
    agentChain: ['ASR', 'Memory', 'Generation', 'Compliance']
  }
];

const mockGeneratedContents: Record<string, GeneratedContent> = {
  'gen_topic_001': {
    id: 'gen_topic_001',
    title: '现金流断裂如何自救',
    hook: '从负债500万到3年翻身，我只做对了一件事...',
    story: '2022年，我的公司现金流断裂，负债500万。那时我每天都在想，是申请破产还是继续坚持？直到有一天，我看到了一个数据：90%的企业倒闭不是因为没利润，而是因为现金流管理出了问题。那一刻，我意识到我必须改变。',
    opinion: '现金流管理比利润更重要。利润是面子，现金流是里子。很多企业看起来很赚钱，但账上没钱，发不出工资，这就是现金流危机。记住：现金流是企业的血液，没有血液，企业就会死亡。',
    cta: '如果你也在为现金流发愁，评论区扣"现金流"，我把我的翻身方法论分享给你。',
    style: 'angry',
    catchphrases: ['记住', '那一刻'],
    sourceTracing: [
      { section: 'hook', sourceId: 'story_003', sourceType: 'story', matchScore: 85 },
      { section: 'story', sourceId: 'story_003', sourceType: 'story', matchScore: 92 },
    ],
    compliance: {
      originalityScore: 82,
      sensitiveWords: [],
      platformChecks: {
        douyin: 'passed',
        xiaohongshu: 'passed'
      }
    },
    agentChain: ['Strategy', 'Memory', 'Generation', 'Compliance'],
    createdAt: '2026-03-18T02:00:00Z'
  },
  'gen_remix_001': {
    id: 'gen_remix_001',
    title: '副业选择的5个真相',
    hook: '月薪3千和月薪3万的人，差距根本不在这8小时...',
    story: '我见过太多人，白天上班摸鱼，晚上回家刷剧。他们抱怨工资低，却从不行动。但真正改变命运的，往往是下班后那4个小时。2021年，我也是个月薪5千的打工人，但用了2年时间，我把副业做成了主业，收入翻了10倍。',
    opinion: '副业不是雪中送炭，而是锦上添花。最好的副业，是和主业有协同效应的。比如你是设计师，可以接私单；你是程序员，可以做独立开发。不要从零开始，要从你的优势出发。',
    cta: '想知道我如何找到副业的第一个客户吗？关注我，下期告诉你我的获客秘诀。',
    style: 'angry',
    sourceTracing: [],
    compliance: {
      originalityScore: 78,
      sensitiveWords: [],
      platformChecks: {
        douyin: 'passed',
        xiaohongshu: 'passed'
      }
    },
    agentChain: ['Remix', 'Memory', 'Generation', 'Compliance'],
    createdAt: '2026-03-18T02:00:00Z'
  },
  'gen_original_001': {
    id: 'gen_original_001',
    title: '30岁创业者的真实感悟',
    hook: '30岁那年，我终于明白了一个道理...',
    story: '30岁之前，我以为成功是线性的。好好学习，考上好大学，找个好工作，然后升职加薪。但30岁那年，公司裁员，我成了被优化掉的那一个。那一刻我才明白，打工永远是在为别人铺路，只有创业才是为自己积累资产。',
    opinion: '创业不是赌博，而是有准备的冒险。在你辞职之前，先用业余时间验证你的商业模式。当你副业收入超过主业3倍的时候，才是辞职的最好时机。',
    cta: '30岁不是终点，而是新的起点。你敢不敢在评论区留下你的年龄和梦想？',
    style: 'calm',
    sourceTracing: [],
    compliance: {
      originalityScore: 88,
      sensitiveWords: [],
      platformChecks: {
        douyin: 'passed',
        xiaohongshu: 'passed'
      }
    },
    agentChain: ['ASR', 'Memory', 'Generation', 'Compliance'],
    createdAt: '2026-03-18T02:00:00Z'
  }
};

const mockAgentStatus: AgentConfigStatus = {
  strategy: {
    status: 'ready',
    config: ['四维权重', '竞品监控列表', '选题黑名单'],
    lastUpdated: '2026-03-15'
  },
  memory: {
    status: 'ready',
    config: ['情绪/场景/认知标签', '混合检索策略', '素材使用追踪'],
    lastUpdated: '2026-03-16'
  },
  analytics: {
    status: 'ready',
    config: ['播放量预测', '完播率预测'],
    lastUpdated: '2026-03-15'
  },
  remix: {
    status: 'ready',
    config: ['结构解构规则', '原创度阈值<25%'],
    lastUpdated: '2026-03-17'
  },
  asr: {
    status: 'ready',
    config: ['Whisper API连接正常'],
    lastUpdated: '2026-03-10'
  },
  generation: {
    status: 'ready',
    config: ['50篇S级训练文本', '3种情绪风格', '口头禅配置'],
    lastUpdated: '2026-03-16'
  },
  compliance: {
    status: 'ready',
    config: ['三级敏感词库', '平台规则库'],
    lastUpdated: '2026-03-18'
  }
};

// ===== API实现 =====
const USE_MOCK = false; // 设置为false时连接真实后端

/** 与 lib/api.ts 一致：Railway 生产环境依赖 X-API-Key（须与后端 API_KEY 相同） */
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';

async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  if (USE_MOCK) {
    throw new Error('Mock mode: API not implemented');
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string> | undefined),
  };
  if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
  }
  const jwt = typeof window !== 'undefined' ? getStoredToken() : null;
  if (jwt) {
    headers.Authorization = `Bearer ${jwt}`;
  }

  const response = await fetch(`${getApiOriginOrEmpty()}${endpoint}`, {
    ...options,
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  
  return response.json();
}

export const creatorApi = {
  // ===== Agent配置状态 =====
  async getAgentConfigStatus(): Promise<AgentConfigStatus> {
    if (USE_MOCK) {
      return mockAgentStatus;
    }
    return apiFetch('/api/creator/agent-status');
  },

  /** 仿写 Tab：抖音低粉爆款（关键词匹配）+ 可选小红书话题笔记 */
  async getRemixRecommendations(ipId: string = 'xiaomin1'): Promise<RemixRecommendationItem[]> {
    if (USE_MOCK) {
      await new Promise((r) => setTimeout(r, 400));
      return [
        {
          url: 'https://www.douyin.com/',
          title: '示例：配置 TIKHUB_API_KEY 后替换为真实推荐',
          platform: 'douyin',
          reason: 'Mock',
        },
      ];
    }
    const resp = await apiFetch<{ items: RemixRecommendationItem[] }>(
      `/api/creator/remix/recommendations?ipId=${encodeURIComponent(ipId)}`
    );
    return resp.items || [];
  },

  // ===== 场景一：推荐选题 =====
  async getRecommendedTopics(ipId: string = 'xiaomin1'): Promise<TopicCard[]> {
    if (USE_MOCK) {
      return mockTopics;
    }
    const resp = await apiFetch<{ topics: TopicCard[] }>(
      `/api/creator/topics/recommended?ipId=${encodeURIComponent(ipId)}`
    );
    return resp.topics || [];
  },

  async refreshTopics(ipId: string = 'xiaomin1'): Promise<TopicCard[]> {
    if (USE_MOCK) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      return [...mockTopics].sort(() => Math.random() - 0.5);
    }
    const resp = await apiFetch<{ topics: TopicCard[] }>(
      `/api/creator/topics/refresh?ipId=${encodeURIComponent(ipId)}`
    );
    return resp.topics || [];
  },

  // 场景一第二步：选中推荐选题后生成正文
  async generateFromTopic(
    topicId: string,
    topicTitle: string,
    style: StyleType,
    ipId: string = 'xiaomin1'
  ): Promise<GenerateResult> {
    console.log('[API] Generate from topic:', { topicId, topicTitle, style, ipId });
    
    if (USE_MOCK) {
      await new Promise(resolve => setTimeout(resolve, 1500));
      return {
        id: `gen_${topicId}`,
        status: 'completed',
        progress: 100,
        estimatedTime: 0
      };
    }
    
    return apiFetch('/api/creator/generate/topic', {
      method: 'POST',
      body: JSON.stringify({ topicId, topicTitle, style, ipId })
    });
  },

  // ===== 场景二：仿写爆款 =====
  async generateFromRemix(url: string, style: StyleType, ipId: string = 'xiaomin1'): Promise<GenerateResult> {
    console.log('[API] Generate from remix:', { url, style, ipId });
    
    if (USE_MOCK) {
      await new Promise(resolve => setTimeout(resolve, 2000));
      return {
        id: 'gen_remix_001',
        status: 'completed',
        progress: 100,
        estimatedTime: 0
      };
    }
    
    return apiFetch('/api/creator/generate/remix', {
      method: 'POST',
      body: JSON.stringify({ url, style, ipId })
    });
  },

  // ===== 场景三：爆款原创（支持文本/语音输入）=====
  async generateFromOriginal(text: string, style: StyleType): Promise<GenerateResult> {
    console.log('[API] Generate from original:', { text, style });
    
    if (USE_MOCK) {
      await new Promise(resolve => setTimeout(resolve, 1500));
      return {
        id: 'gen_original_001',
        status: 'completed',
        progress: 100,
        estimatedTime: 0
      };
    }
    
    return apiFetch('/api/creator/generate/original', {
      method: 'POST',
      body: JSON.stringify({ text, style })
    });
  },

  // 兼容旧调用：voice 已重命名为 original
  async generateFromVoice(text: string, style: StyleType): Promise<GenerateResult> {
    return this.generateFromOriginal(text, style);
  },

  // ===== 场景三：爆款原创（工业化流水线）=====
  async generateViralOriginal(params: {
    input: string;
    inputMode: 'text' | 'voice' | 'file';
    scriptTemplate: string;
    viralElements: string[];
    targetDuration: number;
    style: StyleType;
    ipId?: string;
    customScriptHint?: string;
  }): Promise<GenerateResult> {
    console.log('[API] Generate viral original:', params);
    
    if (USE_MOCK) {
      // 模拟工业化流水线7步精加工过程
      await new Promise(resolve => setTimeout(resolve, 2500));
      return {
        id: 'gen_viral_001',
        status: 'completed',
        progress: 100,
        estimatedTime: 0
      };
    }
    
    return apiFetch('/api/creator/generate/viral', {
      method: 'POST',
      body: JSON.stringify(params)
    });
  },

  // ===== 获取生成进度 =====
  async getGenerationProgress(id: string): Promise<GenerateResult> {
    if (USE_MOCK) {
      return {
        id,
        status: 'completed',
        progress: 100,
        estimatedTime: 0
      };
    }
    return apiFetch(`/api/creator/generate/${id}/progress`);
  },

  // ===== 获取生成结果 =====
  async getGeneratedContent(id: string): Promise<GeneratedContent> {
    if (USE_MOCK) {
      // 模拟延迟
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // 根据ID返回对应的内容
      if (mockGeneratedContents[id]) {
        return mockGeneratedContents[id];
      }
      
      // 如果找不到，返回默认内容
      return mockGeneratedContents['gen_topic_001'];
    }
    return apiFetch(`/api/creator/generate/${id}/result`);
  },

  // ===== 内容库 =====
  async getLibraryItems(status?: string): Promise<LibraryItem[]> {
    if (USE_MOCK) {
      await new Promise(resolve => setTimeout(resolve, 800));
      
      if (!status || status === 'all') {
        return mockLibraryItems;
      }
      
      return mockLibraryItems.filter(item => item.status === status);
    }
    
    const url = status ? `/api/creator/library?status=${status}` : '/api/creator/library';
    return apiFetch(url);
  },

  async deleteLibraryItem(id: string): Promise<void> {
    if (USE_MOCK) {
      await new Promise((resolve) => setTimeout(resolve, 400));
      const idx = mockLibraryItems.findIndex((x) => x.id === id);
      if (idx >= 0) {
        mockLibraryItems.splice(idx, 1);
      }
      return;
    }
    await apiFetch<{ ok: boolean }>(`/api/creator/library/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    });
  },

  async publishContent(id: string, platforms: string[]): Promise<void> {
    console.log('Publish:', { id, platforms });
    
    if (USE_MOCK) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      return;
    }
    
    return apiFetch('/api/creator/publish', {
      method: 'POST',
      body: JSON.stringify({ id, platforms })
    });
  },

  // ===== 数据分析 =====
  async getAnalytics(): Promise<AnalyticsMetrics> {
    if (USE_MOCK) {
      await new Promise(resolve => setTimeout(resolve, 600));
      return {
        published: 12,
        viral: 2,
        leads: 156,
        viralRate: 16.7,
        completionRate: 38.5,
        engagementRate: 5.2,
        suggestions: [
          {
            id: '1',
            type: 'hook',
            title: '优化钩子',
            description: '黄金3秒加入具体数字，完播率可提升20%',
            priority: 'high'
          },
          {
            id: '2',
            type: 'timing',
            title: '发布时间',
            description: '尝试在晚上7-9点发布，获得更多流量',
            priority: 'medium'
          },
          {
            id: '3',
            type: 'style',
            title: '风格调整',
            description: '在CTA部分增加互动引导，有助于提升评论率',
            priority: 'medium'
          }
        ]
      };
    }
    return apiFetch('/api/creator/analytics');
  },
};

// ===== 重新导出类型 =====
export type { TopicCard, GeneratedContent, LibraryItem, AnalyticsMetrics, StyleType };
