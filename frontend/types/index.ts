// IP Types
export interface IP {
  ip_id: string;
  name: string;
  owner_user_id: string;
  status: 'active' | 'inactive' | 'suspended';
  created_at?: string;
  updated_at?: string;
  
  // 账号体系：超级符号识别系统（7个标准化触点）
  avatar_url?: string;
  nickname?: string;
  bio?: string;
  cover_image_url?: string;
  cover_template?: string;
  pinned_content?: string;
  like_follower_ratio?: string;
  
  // 商业定位：变现前置原则
  monetization_model?: string;
  target_audience?: string;
  content_direction?: string;
  unique_value_prop?: string;
  
  // 定位交叉点：擅长 × 热爱 × 市场需求
  expertise?: string;
  passion?: string;
  market_demand?: string;
  
  // 变现象限：产品/服务 × 客单价 × 复购率
  product_service?: string;
  price_range?: string;
  repurchase_rate?: string;
}

export interface CreateIPRequest {
  ip_id: string;
  name: string;
  owner_user_id: string;
  status?: string;
  
  // 账号体系字段
  avatar_url?: string;
  nickname?: string;
  bio?: string;
  cover_image_url?: string;
  cover_template?: string;
  pinned_content?: string;
  like_follower_ratio?: string;
  
  // 商业定位字段
  monetization_model?: string;
  target_audience?: string;
  content_direction?: string;
  unique_value_prop?: string;
  
  // 定位交叉点字段
  expertise?: string;
  passion?: string;
  market_demand?: string;
  
  // 变现象限字段
  product_service?: string;
  price_range?: string;
  repurchase_rate?: string;
}

// Memory Types
export interface IngestRequest {
  ip_id: string;
  source_type: 'video' | 'audio' | 'text' | 'document';
  source_url?: string;
  local_file_id?: string;
  title?: string;
  notes?: string;
}

export interface IngestResponse {
  ingest_task_id: string;
  status: string;
}

/** POST /memory/upload */
export interface MemoryUploadResponse {
  file_id: string;
  file_url: string;
  size_bytes: number;
  content_type?: string | null;
}

export interface IngestStatus {
  ingest_task_id: string;
  status: 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  error?: string;
  created_assets: string[];
}

/** GET /memory/assets 单条素材摘要 */
export interface MemoryAssetItem {
  asset_id: string;
  title?: string;
  content_snippet?: string;
  asset_type: string;
  metadata: Record<string, unknown>;
}

export interface AssetsListResponse {
  items: MemoryAssetItem[];
  total: number;
}

export interface RetrieveRequest {
  ip_id: string;
  query: string;
  filters?: {
    emotion_tags?: string[];
    scene_tags?: string[];
    max_usage_ratio?: number;
  };
  top_k?: number;
}

export interface RetrieveResult {
  asset_id: string;
  title?: string;
  content_snippet?: string;
  metadata: Record<string, any>;
  similarity: number;
}

// Tag Config Types
export interface TagCategoryValue {
  value: string;
  label: string;
  color: string;
  enabled: boolean;
}

export interface TagCategory {
  name: string;
  level: number;
  type: string;
  values: TagCategoryValue[];
}

export interface TagConfig {
  config_id: string;
  ip_id: string;
  tag_categories: TagCategory[];
  version: number;
  updated_by: string;
  updated_at: string;
}

// Memory Config Types
export interface RetrievalConfig {
  strategy: string;
  top_k: number;
  min_similarity: number;
  diversity_enabled: boolean;
  diversity_recent_window: number;
  freshness_weight: number;
}

export interface UsageLimitsConfig {
  core_max_usage: number;
  normal_max_usage: number;
  disposable_max_usage: number;
  exceed_behavior: string;
}

export interface MemoryConfig {
  config_id: string;
  ip_id: string;
  retrieval: RetrievalConfig;
  usage_limits: UsageLimitsConfig;
  version: number;
  updated_by: string;
  updated_at: string;
}

export interface MemoryFullConfig {
  tag_config?: TagConfig;
  memory_config?: MemoryConfig;
}

// Agent Types
export interface Agent {
  id: string;
  name: string;
  nameEn: string;
  description: string;
  icon: string;
  color: string;
  status: 'active' | 'inactive' | 'configuring';
  config?: Record<string, any>;
}

// Dashboard Types
export interface DashboardStats {
  total_content: number;
  daily_output: number;
  approval_rate: number;
  avg_quality_score: number;
  cost_per_content: number;
  time_saved: number;
}

export interface WorkflowStatus {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'failed' | 'pending';
  progress: number;
  startTime?: string;
  endTime?: string;
  agent?: string;
}

// Feishu integration
export interface FeishuConfig {
  configured: boolean;
  app_id: string;
  has_secret: boolean;
}

export interface FeishuConfigSave {
  app_id: string;
  app_secret: string;
}

export interface FeishuSpaceItem {
  space_id: string;
  name?: string;
  description?: string;
}

export interface FeishuSyncResult {
  synced: number;
  skipped?: number;
  deleted?: number;
  failed: number;
  total_remote?: number;
  total_local?: number;
  errors: string[];
  used_space_id?: string | null;
}

export interface FeishuBinding {
  ip_id: string;
  space_id: string;
  space_name?: string;
}

// 待办标签 / 更新标签
export interface PendingLabelsItem {
  asset_id: string;
  title?: string;
  source?: string;
  content_snippet?: string;
  auto_labels: Record<string, unknown>;
}

export interface UpdateLabelsRequest {
  ip_id: string;
  confirmed_labels: Record<string, unknown>;
}

// Config history
export interface ConfigHistoryItem {
  id: string;
  agent: string;
  action: string;
  user: string;
  time: string;
  version: number;
}

// ==================== 混合检索 ====================
export interface HybridRetrieveRequest {
  ip_id: string;
  query: string;
  top_k?: number;
  vector_weight?: number;
  graph_weight?: number;
  use_vector?: boolean;
  use_graph?: boolean;
}

export interface HybridRetrieveResult {
  query: string;
  ip_id: string;
  total: number;
  results: Array<{
    asset_id: string;
    hybrid_score: number;
    sources: string[];
    vector_score?: number;
    graph_score?: number;
    content?: string;
    metadata?: Record<string, any>;
    relation?: string;
  }>;
  config: {
    vector_weight: number;
    graph_weight: number;
    fusion_method: string;
  };
}

// ==================== 记忆Consolidation ====================
export interface MemoryConsolidateResult {
  total_assets: number;
  promoted: number;
  demoted: number;
  archived: number;
  core_summary?: string;
}

export interface MemorySummaryResult {
  stats: {
    total: number;
    by_level: Record<string, number>;
    avg_usage: number;
  };
  core_memory: Array<{
    asset_id: string;
    title: string;
    content_snippet: string;
    usage_count: number;
  }>;
  archived_memory: Array<{
    asset_id: string;
    title: string;
    content_snippet: string;
  }>;
}

export interface CoreMemoryResult {
  items: Array<{
    asset_id: string;
    title: string;
    content_snippet: string;
    usage_count: number;
    last_used_at?: string;
  }>;
}

export interface TimeWeightedRequest {
  ip_id: string;
  query: string;
  top_k?: number;
  time_weight?: number;
}

export interface TimeWeightedResult {
  query: string;
  total: number;
  results: Array<{
    asset_id: string;
    title: string;
    content_snippet: string;
    score: number;
    level: string;
    time_score: number;
    usage_score: number;
  }>;
}

// ==================== Graph RAG ====================
export interface GraphBuildRequest {
  ip_id: string;
  force_rebuild?: boolean;
}

export interface GraphBuildResult {
  entities: number;
  relations: number;
  errors: string[];
}

export interface GraphRetrieveRequest {
  ip_id: string;
  query: string;
  depth?: number;
  limit?: number;
}

export interface GraphRetrieveResult {
  seed_nodes: Array<{
    name: string;
    type: string;
    description: string;
  }>;
  paths: Array<{
    from: string;
    relation: string;
    to: string;
    context: string;
  }>;
}

export interface GraphStatsResult {
  nodes: Record<string, number>;
  relations: Record<string, number>;
  total_nodes: number;
  total_relations: number;
}

// ==================== 多模态 ====================
export interface VideoAnalyzeResult {
  analysis: string;
  keyframes_count: number;
  frames_analyzed: number;
}

export interface ImageAnalyzeResult {
  analysis: string;
}

export interface AudioTopicsResult {
  topics?: string[];
  core_points?: string[];
  sentiment?: string;
  content_types?: string[];
  raw_analysis?: string;
}
