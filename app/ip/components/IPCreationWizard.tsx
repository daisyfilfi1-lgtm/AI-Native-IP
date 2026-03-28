'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { 
  ChevronRight,
  Target, 
  User, 
  Sparkles,
  CheckCircle2,
  DollarSign,
  Users,
  Heart,
  Brain,
  TrendingUp,
  Lightbulb,
  FileText,
  Loader2,
  AlertCircle
} from 'lucide-react';

// 四大变现模式
const MONETIZATION_MODELS = [
  {
    id: 'knowledge',
    name: '知识付费',
    emoji: '📚',
    desc: '课程/咨询/训练营',
    fit: '专业人士/行业经验者',
    content: '干货密度高、人设权威',
    fans: '1万+精准粉',
    efficiency: 5,
    color: 'from-blue-500 to-cyan-500'
  },
  {
    id: 'ecommerce',
    name: '电商带货',
    emoji: '🛍️',
    desc: '供应链/选品能力',
    fit: '供应链/选品能力强',
    content: '产品展示、使用场景',
    fans: '5千+',
    efficiency: 4,
    color: 'from-green-500 to-emerald-500'
  },
  {
    id: 'advertising',
    name: '广告分成',
    emoji: '📺',
    desc: '流量变现',
    fit: '泛内容创作者',
    content: '娱乐性强、完播率高',
    fans: '10万+',
    efficiency: 3,
    color: 'from-purple-500 to-pink-500'
  },
  {
    id: 'private',
    name: '私域引流',
    emoji: '💬',
    desc: '高客单服务/本地商家',
    fit: '高客单服务/本地商家',
    content: '信任建立、案例展示',
    fans: '精准即可',
    efficiency: 5,
    color: 'from-orange-500 to-amber-500'
  }
];

// 2个核心超级符号触点
const TOUCHPOINTS = [
  { id: 'nickname', name: '昵称', icon: FileText, desc: '行业标签+人名，避免生僻字', placeholder: '例如：张凯聊运营、李姐说育儿...' },
  { id: 'bio', name: '简介', icon: FileText, desc: '痛点承诺+解决方案+社会证明', placeholder: '例如：帮助1000+商家实现流量破圈，专注私域变现...' },
];

interface IPCreationWizardProps {
  onComplete: (data: IPFormData) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export interface IPFormData {
  // 基础信息
  ip_id: string;
  name: string;
  owner_user_id: string;
  
  // 商业定位
  monetization_model: string;
  target_audience: string;
  content_direction: string;
  unique_value_prop: string;
  
  // 定位交叉点
  expertise: string;
  passion: string;
  market_demand: string;
  
  // 变现象限
  product_service: string;
  price_range: string;
  repurchase_rate: string;
  
  // 超级符号识别系统
  nickname: string;
  bio: string;
}

const steps = [
  { id: 'basic', name: '基础信息', icon: User },
  { id: 'positioning', name: '商业定位', icon: Target },
  { id: 'crosspoint', name: '定位交叉点', icon: Lightbulb },
  { id: 'monetization', name: '变现象限', icon: DollarSign },
  { id: 'touchpoints', name: '超级符号', icon: Sparkles },
  { id: 'review', name: '确认创建', icon: CheckCircle2 },
];

export function IPCreationWizard({ onComplete, onCancel, isLoading }: IPCreationWizardProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<IPFormData>({
    ip_id: '',
    name: '',
    owner_user_id: 'admin',
    monetization_model: '',
    target_audience: '',
    content_direction: '',
    unique_value_prop: '',
    expertise: '',
    passion: '',
    market_demand: '',
    product_service: '',
    price_range: '',
    repurchase_rate: '',
    nickname: '',
    bio: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const updateField = (field: keyof IPFormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const validateStep = () => {
    const newErrors: Record<string, string> = {};
    
    switch (currentStep) {
      case 0: // 基础信息
        if (!formData.name.trim()) newErrors.name = '请输入IP名称';
        if (!formData.ip_id.trim()) newErrors.ip_id = '请输入IP ID';
        if (!/^[a-zA-Z0-9_-]+$/.test(formData.ip_id)) newErrors.ip_id = 'IP ID只能包含字母、数字、下划线和横线';
        break;
      case 1: // 商业定位
        if (!formData.monetization_model) newErrors.monetization_model = '请选择变现模式';
        if (!formData.target_audience.trim()) newErrors.target_audience = '请输入目标受众';
        break;
      case 2: // 定位交叉点
        if (!formData.expertise.trim()) newErrors.expertise = '请输入擅长领域';
        if (!formData.passion.trim()) newErrors.passion = '请输入热爱领域';
        break;
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (validateStep()) {
      setCurrentStep(prev => Math.min(prev + 1, steps.length - 1));
    }
  };

  const handleBack = () => {
    setCurrentStep(prev => Math.max(prev - 1, 0));
  };

  const handleSubmit = () => {
    onComplete(formData);
  };

  const renderStep = () => {
    switch (currentStep) {
      case 0: // 基础信息
        return (
          <div className="space-y-6">
            <div className="p-4 bg-background-tertiary rounded-xl">
              <h3 className="font-medium text-foreground mb-2 flex items-center gap-2">
                <User className="w-4 h-4 text-primary-400" />
                基础信息
              </h3>
              <p className="text-sm text-foreground-secondary">
                创建IP的基本信息，这是IP的身份证
              </p>
            </div>

            <Input
              label="IP名称"
              placeholder="例如：张凯"
              helper="显示名称，建议使用真实姓名或品牌名"
              value={formData.name}
              onChange={(e) => updateField('name', e.target.value)}
              error={errors.name}
            />

            <Input
              label="IP ID"
              placeholder="例如：zhangkai_001"
              helper="唯一标识符，创建后不可修改，只能包含字母、数字、下划线"
              value={formData.ip_id}
              onChange={(e) => updateField('ip_id', e.target.value)}
              error={errors.ip_id}
            />

            <Input
              label="负责人 ID"
              placeholder="例如：admin"
              helper="归属运营/管理账号"
              value={formData.owner_user_id}
              onChange={(e) => updateField('owner_user_id', e.target.value)}
            />
          </div>
        );

      case 1: // 商业定位
        const selectedModel = MONETIZATION_MODELS.find(m => m.id === formData.monetization_model);
        
        return (
          <div className="space-y-6">
            <div className="p-4 bg-gradient-to-r from-primary-500/10 to-accent-cyan/10 rounded-xl border border-primary-500/20">
              <h3 className="font-medium text-foreground mb-2 flex items-center gap-2">
                <Target className="w-4 h-4 text-primary-400" />
                商业定位决策
              </h3>
              <p className="text-sm text-foreground-secondary">
                <span className="text-primary-400 font-medium">变现前置原则：</span>
                变现方式必须在内容生产前确定
              </p>
            </div>

            {errors.monetization_model && (
              <div className="p-3 bg-accent-red/10 border border-accent-red/20 rounded-lg flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-accent-red" />
                <span className="text-sm text-accent-red">{errors.monetization_model}</span>
              </div>
            )}

            {/* 变现模式选择 */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-3">
                选择变现模式 <span className="text-accent-red">*</span>
              </label>
              <div className="grid grid-cols-2 gap-3">
                {MONETIZATION_MODELS.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => updateField('monetization_model', model.id)}
                    className={`p-4 rounded-xl border-2 text-left transition-all ${
                      formData.monetization_model === model.id
                        ? 'border-primary-500 bg-primary-500/10'
                        : 'border-border bg-background-tertiary hover:border-border-hover'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <span className="text-2xl">{model.emoji}</span>
                      <div className="flex gap-0.5">
                        {Array.from({ length: 5 }).map((_, i) => (
                          <span 
                            key={i} 
                            className={`text-xs ${i < model.efficiency ? 'text-accent-yellow' : 'text-foreground-muted'}`}
                          >
                            ⭐
                          </span>
                        ))}
                      </div>
                    </div>
                    <h4 className="font-semibold text-foreground mb-1">{model.name}</h4>
                    <p className="text-xs text-foreground-secondary">{model.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* 选中模式的详情 */}
            {selectedModel && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 bg-background-tertiary rounded-xl border border-border"
              >
                <h4 className="font-medium text-foreground mb-3 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-accent-green" />
                  {selectedModel.name} 适配模型
                </h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-foreground-tertiary block text-xs mb-1">适合人群</span>
                    <span className="text-foreground">{selectedModel.fit}</span>
                  </div>
                  <div>
                    <span className="text-foreground-tertiary block text-xs mb-1">内容特征</span>
                    <span className="text-foreground">{selectedModel.content}</span>
                  </div>
                  <div>
                    <span className="text-foreground-tertiary block text-xs mb-1">粉丝要求</span>
                    <span className="text-foreground">{selectedModel.fans}</span>
                  </div>
                </div>
              </motion.div>
            )}

            <Input
              label="目标受众"
              placeholder="例如：25-35岁职场人士、宝妈群体、创业者..."
              helper="精准描述你的目标受众人群"
              value={formData.target_audience}
              onChange={(e) => updateField('target_audience', e.target.value)}
              error={errors.target_audience}
            />

            <Input
              label="内容方向"
              placeholder="例如：职场成长、育儿经验、商业思维..."
              helper="确定你的核心内容领域"
              value={formData.content_direction}
              onChange={(e) => updateField('content_direction', e.target.value)}
            />

            <Input
              label="独特价值主张"
              placeholder="例如：用3年大厂经验帮你避开职场坑..."
              helper="一句话说明你能为目标受众提供什么独特价值"
              value={formData.unique_value_prop}
              onChange={(e) => updateField('unique_value_prop', e.target.value)}
            />
          </div>
        );

      case 2: // 定位交叉点
        return (
          <div className="space-y-6">
            <div className="p-4 bg-gradient-to-r from-amber-500/10 to-orange-500/10 rounded-xl border border-amber-500/20">
              <h3 className="font-medium text-foreground mb-2 flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-amber-400" />
                定位交叉点
              </h3>
              <p className="text-sm text-foreground-secondary">
                用矩阵确定你的定位交叉点，找到可持续的内容方向
              </p>
            </div>

            {/* 视觉化矩阵 */}
            <div className="p-6 bg-background-tertiary rounded-xl border border-border">
              <div className="text-center mb-6">
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-background-elevated rounded-full">
                  <Brain className="w-4 h-4 text-primary-400" />
                  <span className="text-sm font-medium">能力象限</span>
                </div>
              </div>
              
              <div className="flex items-center justify-center gap-4 mb-6">
                <div className="text-center">
                  <Input
                    placeholder="你擅长的"
                    value={formData.expertise}
                    onChange={(e) => updateField('expertise', e.target.value)}
                    error={errors.expertise}
                    className="w-32 text-center"
                  />
                  <span className="text-xs text-foreground-tertiary mt-1 block">擅长</span>
                </div>
                <span className="text-xl text-foreground-secondary">×</span>
                <div className="text-center">
                  <Input
                    placeholder="你热爱的"
                    value={formData.passion}
                    onChange={(e) => updateField('passion', e.target.value)}
                    error={errors.passion}
                    className="w-32 text-center"
                  />
                  <span className="text-xs text-foreground-tertiary mt-1 block">热爱</span>
                </div>
                <span className="text-xl text-foreground-secondary">×</span>
                <div className="text-center">
                  <Input
                    placeholder="市场需要的"
                    value={formData.market_demand}
                    onChange={(e) => updateField('market_demand', e.target.value)}
                    className="w-32 text-center"
                  />
                  <span className="text-xs text-foreground-tertiary mt-1 block">市场需求</span>
                </div>
              </div>

              <div className="text-center">
                <span className="text-2xl text-foreground-secondary">↓</span>
              </div>

              <div className="mt-4 p-4 bg-gradient-to-r from-primary-500/10 to-accent-cyan/10 rounded-xl">
                <div className="text-center">
                  <span className="text-sm text-foreground-tertiary">内容方向 = </span>
                  <span className="text-lg font-semibold text-primary-400 ml-2">
                    {formData.expertise && formData.passion && formData.market_demand
                      ? `${formData.expertise} × ${formData.passion} × ${formData.market_demand}`
                      : '完善上方信息生成定位'}
                  </span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-background-tertiary rounded-xl">
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="w-4 h-4 text-blue-400" />
                  <span className="font-medium text-sm">擅长领域</span>
                </div>
                <p className="text-xs text-foreground-secondary">
                  你已经具备的专业技能或经验，是你可以持续输出的底气
                </p>
              </div>
              <div className="p-4 bg-background-tertiary rounded-xl">
                <div className="flex items-center gap-2 mb-2">
                  <Heart className="w-4 h-4 text-red-400" />
                  <span className="font-medium text-sm">热爱领域</span>
                </div>
                <p className="text-xs text-foreground-secondary">
                  你真正感兴趣的话题，只有热爱才能支撑长期创作
                </p>
              </div>
              <div className="p-4 bg-background-tertiary rounded-xl">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="w-4 h-4 text-green-400" />
                  <span className="font-medium text-sm">市场需求</span>
                </div>
                <p className="text-xs text-foreground-secondary">
                  有人愿意为此付费或花时间，确保商业价值
                </p>
              </div>
            </div>
          </div>
        );

      case 3: // 变现象限
        const selectedModelInfo = MONETIZATION_MODELS.find(m => m.id === formData.monetization_model);
        
        return (
          <div className="space-y-6">
            <div className="p-4 bg-gradient-to-r from-green-500/10 to-emerald-500/10 rounded-xl border border-green-500/20">
              <h3 className="font-medium text-foreground mb-2 flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-green-400" />
                变现象限
              </h3>
              <p className="text-sm text-foreground-secondary">
                明确你的商业模式：产品/服务 × 客单价 × 复购率
              </p>
            </div>

            {/* 已选的变现模式 */}
            {selectedModelInfo && (
              <div className="p-4 bg-background-tertiary rounded-xl border border-border">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{selectedModelInfo.emoji}</span>
                  <div>
                    <span className="text-sm text-foreground-tertiary">已选变现模式</span>
                    <h4 className="font-semibold text-foreground">{selectedModelInfo.name}</h4>
                  </div>
                </div>
              </div>
            )}

            <Input
              label="产品/服务"
              placeholder="例如：99元职场入门课、1999元私域训练营、企业咨询服务..."
              helper="你具体卖什么？可以是实体产品、课程、服务等多种形式"
              value={formData.product_service}
              onChange={(e) => updateField('product_service', e.target.value)}
            />

            <div>
              <label className="block text-sm font-medium text-foreground mb-3">
                客单价区间
              </label>
              <div className="grid grid-cols-4 gap-2">
                {['0-100元', '100-1000元', '1000-10000元', '10000元+'].map((range) => (
                  <button
                    key={range}
                    onClick={() => updateField('price_range', range)}
                    className={`p-3 rounded-xl border text-center transition-all ${
                      formData.price_range === range
                        ? 'border-primary-500 bg-primary-500/10 text-primary-400'
                        : 'border-border bg-background-tertiary text-foreground-secondary hover:border-border-hover'
                    }`}
                  >
                    {range}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-3">
                预期复购率
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { value: '低复购', desc: '一次性消费' },
                  { value: '中复购', desc: '季度/年度' },
                  { value: '高复购', desc: '月度/高频' }
                ].map((item) => (
                  <button
                    key={item.value}
                    onClick={() => updateField('repurchase_rate', item.value)}
                    className={`p-3 rounded-xl border text-center transition-all ${
                      formData.repurchase_rate === item.value
                        ? 'border-primary-500 bg-primary-500/10 text-primary-400'
                        : 'border-border bg-background-tertiary text-foreground-secondary hover:border-border-hover'
                    }`}
                  >
                    <div className="font-medium">{item.value}</div>
                    <div className="text-xs text-foreground-tertiary mt-1">{item.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* 商业模式预览 */}
            {(formData.product_service || formData.price_range) && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 bg-gradient-to-r from-green-500/10 to-emerald-500/10 rounded-xl border border-green-500/20"
              >
                <h4 className="font-medium text-foreground mb-2">商业模式预览</h4>
                <p className="text-sm text-foreground-secondary">
                  {formData.product_service || '待填写产品/服务'} × {formData.price_range || '待填写客单价'} × {formData.repurchase_rate || '待填写复购率'} = {selectedModelInfo?.name || '商业模式'}
                </p>
              </motion.div>
            )}
          </div>
        );

      case 4: // 超级符号识别系统
        return (
          <div className="space-y-6">
            <div className="p-4 bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-xl border border-purple-500/20">
              <h3 className="font-medium text-foreground mb-2 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-400" />
                超级符号识别系统
              </h3>
              <p className="text-sm text-foreground-secondary">
                建立2个核心触点（昵称+简介），确保用户3秒内识别账号价值
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {TOUCHPOINTS.map((point, index) => {
                const Icon = point.icon;
                const fieldKey = point.id;
                
                return (
                  <motion.div
                    key={point.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="p-4 bg-background-tertiary rounded-xl border border-border hover:border-primary-500/30 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-lg bg-background-elevated flex items-center justify-center flex-shrink-0">
                        <Icon className="w-5 h-5 text-primary-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <h4 className="font-medium text-foreground">{point.name}</h4>
                          <span className="text-xs text-foreground-muted">{index + 1}/2</span>
                        </div>
                        <p className="text-xs text-foreground-secondary mb-2">{point.desc}</p>
                        <Input
                          placeholder={point.placeholder}
                          value={formData[fieldKey as keyof IPFormData] || ''}
                          onChange={(e) => updateField(fieldKey as keyof IPFormData, e.target.value)}
                          className="text-sm"
                        />
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {/* 完成度提示 */}
            <div className="p-4 bg-background-tertiary rounded-xl">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-foreground">超级符号完善度</span>
                <span className="text-sm text-primary-400">
                  {[
                    formData.nickname,
                    formData.bio
                  ].filter(Boolean).length}/2
                </span>
              </div>
              <Progress 
                value={([
                  formData.nickname,
                  formData.bio
                ].filter(Boolean).length / 2) * 100} 
                size="sm" 
                variant="gradient" 
              />
            </div>
          </div>
        );

      case 5: // 确认创建
        return (
          <div className="space-y-6">
            <div className="p-4 bg-gradient-to-r from-accent-green/10 to-emerald-500/10 rounded-xl border border-accent-green/20">
              <h3 className="font-medium text-foreground mb-2 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-accent-green" />
                确认创建
              </h3>
              <p className="text-sm text-foreground-secondary">
                检查所有信息，确认无误后创建IP
              </p>
            </div>

            {/* 信息汇总卡片 */}
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {/* 基础信息 */}
              <div className="p-4 bg-background-tertiary rounded-xl">
                <h4 className="font-medium text-foreground mb-3 flex items-center gap-2">
                  <User className="w-4 h-4 text-primary-400" />
                  基础信息
                </h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-foreground-tertiary">IP名称：</span>
                    <span className="text-foreground">{formData.name}</span>
                  </div>
                  <div>
                    <span className="text-foreground-tertiary">IP ID：</span>
                    <span className="text-foreground">{formData.ip_id}</span>
                  </div>
                </div>
              </div>

              {/* 商业定位 */}
              <div className="p-4 bg-background-tertiary rounded-xl">
                <h4 className="font-medium text-foreground mb-3 flex items-center gap-2">
                  <Target className="w-4 h-4 text-primary-400" />
                  商业定位
                </h4>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-foreground-tertiary">变现模式：</span>
                    <span className="text-foreground">
                      {MONETIZATION_MODELS.find(m => m.id === formData.monetization_model)?.name || '-'}
                    </span>
                  </div>
                  <div>
                    <span className="text-foreground-tertiary">目标受众：</span>
                    <span className="text-foreground">{formData.target_audience || '-'}</span>
                  </div>
                  <div>
                    <span className="text-foreground-tertiary">内容方向：</span>
                    <span className="text-foreground">{formData.content_direction || '-'}</span>
                  </div>
                </div>
              </div>

              {/* 定位交叉点 */}
              <div className="p-4 bg-background-tertiary rounded-xl">
                <h4 className="font-medium text-foreground mb-3 flex items-center gap-2">
                  <Lightbulb className="w-4 h-4 text-amber-400" />
                  定位交叉点
                </h4>
                <p className="text-sm text-foreground">
                  {formData.expertise || '-'} × {formData.passion || '-'} × {formData.market_demand || '-'}
                </p>
              </div>

              {/* 变现象限 */}
              <div className="p-4 bg-background-tertiary rounded-xl">
                <h4 className="font-medium text-foreground mb-3 flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-green-400" />
                  变现象限
                </h4>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-foreground-tertiary">产品/服务：</span>
                    <span className="text-foreground">{formData.product_service || '-'}</span>
                  </div>
                  <div>
                    <span className="text-foreground-tertiary">客单价：</span>
                    <span className="text-foreground">{formData.price_range || '-'}</span>
                  </div>
                  <div>
                    <span className="text-foreground-tertiary">复购率：</span>
                    <span className="text-foreground">{formData.repurchase_rate || '-'}</span>
                  </div>
                </div>
              </div>

              {/* 超级符号 */}
              <div className="p-4 bg-background-tertiary rounded-xl">
                <h4 className="font-medium text-foreground mb-3 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-400" />
                  超级符号识别系统
                </h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {[
                    { label: '昵称', value: formData.nickname },
                    { label: '简介', value: formData.bio },
                  ].map((item) => (
                    <div key={item.label}>
                      <span className="text-foreground-tertiary">{item.label}：</span>
                      <span className="text-foreground">{item.value || '-'}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  const CurrentStepIcon = steps[currentStep].icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-3xl h-[85vh] flex flex-col"
      >
        <Card className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="p-6 border-b border-border">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-cyan flex items-center justify-center">
                  <CurrentStepIcon className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-foreground">
                    {steps[currentStep].name}
                  </h2>
                  <p className="text-sm text-foreground-secondary">
                    步骤 {currentStep + 1} / {steps.length}
                  </p>
                </div>
              </div>
              <button
                onClick={onCancel}
                className="p-2 rounded-lg hover:bg-background-tertiary transition-colors"
              >
                <span className="sr-only">关闭</span>
                <svg className="w-5 h-5 text-foreground-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Progress bar */}
            <div className="flex items-center gap-2">
              {steps.map((step, index) => {
                const StepIcon = step.icon;
                const isActive = index === currentStep;
                const isCompleted = index < currentStep;
                
                return (
                  <div key={step.id} className="flex items-center flex-1">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                        isActive ? 'bg-primary-500 text-white' :
                        isCompleted ? 'bg-accent-green text-white' :
                        'bg-background-tertiary text-foreground-secondary'
                      }`}
                    >
                      {isCompleted ? (
                        <CheckCircle2 className="w-4 h-4" />
                      ) : (
                        <StepIcon className="w-4 h-4" />
                      )}
                    </div>
                    {index < steps.length - 1 && (
                      <div
                        className={`flex-1 h-0.5 mx-2 ${
                          isCompleted ? 'bg-accent-green' : 'bg-border'
                        }`}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentStep}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
              >
                {renderStep()}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-border flex justify-between">
            <Button
              variant="ghost"
              onClick={currentStep === 0 ? onCancel : handleBack}
              disabled={isLoading}
            >
              {currentStep === 0 ? '取消' : '上一步'}
            </Button>
            
            {currentStep === steps.length - 1 ? (
              <Button
                onClick={handleSubmit}
                isLoading={isLoading}
                leftIcon={!isLoading ? <CheckCircle2 className="w-4 h-4" /> : undefined}
              >
                确认创建
              </Button>
            ) : (
              <Button
                onClick={handleNext}
                rightIcon={<ChevronRight className="w-4 h-4" />}
              >
                下一步
              </Button>
            )}
          </div>
        </Card>
      </motion.div>
    </div>
  );
}

// cn函数
function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(' ');
}
