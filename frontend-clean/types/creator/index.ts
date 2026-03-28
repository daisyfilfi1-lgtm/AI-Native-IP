// IP创作端类型定义

// 选题卡片
export interface TopicCard {
  id: string;
  title: string;
  score: number; // 4.0-5.0
  estimatedViews: string; // "50-80万"
  estimatedCompletion: number; // 32%
  tags: string[]; // ["现金流", "创业"]
  reason: string; // "基于你的故事_003匹配"
}

// 生成内容的段落
export interface Section {
  id: string;
  content: string;
  source?: string; // 素材溯源
  editable: boolean;
}

// 生成结果
export interface GeneratedContent {
  id: string;
  topicId: string;
  status: 'generating' | 'completed' | 'failed';
  sections: {
    hook: Section;
    story: Section;
    opinion: Section;
    cta: Section;
  };
  style: 'angry' | 'calm' | 'humor';
  compliance: {
    originality: number; // 87%
    sensitiveWords: boolean;
    status: 'passed' | 'warning' | 'failed';
  };
  createdAt: string;
}

// 内容库项目
export interface ContentItem {
  id: string;
  title: string;
  status: 'draft' | 'pending' | 'published' | 'hit';
  style: 'angry' | 'calm' | 'humor';
  views?: number;
  likes?: number;
  createdAt: string;
  publishedAt?: string;
  thumbnail?: string;
}

// 数据指标
export interface AnalyticsData {
  publishedCount: number;
  hitCount: number;
  leadsCount: number;
  weeklyGrowth: {
    published: number;
    hit: number;
    leads: number;
  };
  bestContent: {
    id: string;
    title: string;
    views: number;
    likes: number;
  }[];
  suggestions: string[];
}

// 风格选项
export type StyleType = 'angry' | 'calm' | 'humor';

export interface StyleOption {
  value: StyleType;
  label: string;
  emoji: string;
  description: string;
}
