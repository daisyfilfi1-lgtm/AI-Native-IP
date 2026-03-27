'use client';

import { useState, useEffect } from 'react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { 
  Plus, 
  Search, 
  Users, 
  FileText, 
  Settings,
  ExternalLink,
  Loader2,
  Target,
  Sparkles,
  DollarSign,
  TrendingUp
} from 'lucide-react';
import Link from 'next/link';
import { IP } from '@/types';
import { api } from '@/lib/api';
import { IPCreationWizard, IPFormData } from './components/IPCreationWizard';

// 统计为占位（后端暂无内容/素材数接口）
const statsData: Record<string, { content: number; assets: number; lastActive: string }> = {};

// 变现模式映射
const MONETIZATION_LABELS: Record<string, string> = {
  knowledge: '知识付费',
  ecommerce: '电商带货',
  advertising: '广告分成',
  private: '私域引流',
};

export default function IPManagementPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateWizard, setShowCreateWizard] = useState(false);
  const [ips, setIps] = useState<IP[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const list = await api.listIPs();
        setIps(list);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const filteredIPs = ips.filter(ip => 
    ip.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    ip.ip_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreateIP = async (formData: IPFormData) => {
    setCreating(true);
    try {
      await api.createIP({
        ip_id: formData.ip_id,
        name: formData.name,
        owner_user_id: formData.owner_user_id,
        status: 'active',
        // 账号体系字段
        nickname: formData.nickname,
        bio: formData.bio,
        // 商业定位字段
        monetization_model: formData.monetization_model,
        target_audience: formData.target_audience,
        content_direction: formData.content_direction,
        unique_value_prop: formData.unique_value_prop,
        // 定位交叉点字段
        expertise: formData.expertise,
        passion: formData.passion,
        market_demand: formData.market_demand,
        // 变现象限字段
        product_service: formData.product_service,
        price_range: formData.price_range,
        repurchase_rate: formData.repurchase_rate,
      });
      const list = await api.listIPs();
      setIps(list);
      setShowCreateWizard(false);
    } catch (e: any) {
      console.error('Create IP failed:', e);
      alert(e.response?.data?.detail || (e as Error).message || '创建失败');
    } finally {
      setCreating(false);
    }
  };

  return (
    <MainLayout title="IP管理">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground mb-2">IP管理</h1>
        <p className="text-foreground-secondary">
          基于账号体系统一管理你的IP矩阵，每个IP都有完整的商业定位和超级符号识别系统
        </p>
      </div>

      {/* Header actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div className="relative max-w-md w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-tertiary" />
          <Input
            placeholder="搜索IP名称或ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button 
          leftIcon={<Plus className="w-4 h-4" />}
          onClick={() => setShowCreateWizard(true)}
        >
          新建IP
        </Button>
      </div>

      {/* IP Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-12 gap-2 text-foreground-secondary">
          <Loader2 className="w-5 h-5 animate-spin" /> 加载中...
        </div>
      ) : (
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filteredIPs.map((ip) => {
          const stats = statsData[ip.ip_id] || { content: 0, assets: 0, lastActive: '-' };
          
          return (
            <Card key={ip.ip_id} hover className="group">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-accent-cyan flex items-center justify-center text-white font-bold text-lg">
                    {ip.avatar_url ? (
                      <img src={ip.avatar_url} alt={ip.name} className="w-full h-full object-cover rounded-xl" />
                    ) : (
                      ip.name[0]
                    )}
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground">{ip.name}</h3>
                    <p className="text-xs text-foreground-tertiary font-mono">{ip.ip_id}</p>
                    {ip.nickname && (
                      <p className="text-xs text-primary-400">@{ip.nickname}</p>
                    )}
                  </div>
                </div>
                <Badge 
                  variant={ip.status === 'active' ? 'success' : 'default'}
                  dot
                >
                  {ip.status === 'active' ? '活跃' : '停用'}
                </Badge>
              </div>

              {/* 商业定位标签 */}
              {ip.monetization_model && (
                <div className="mb-3">
                  <Badge variant="primary" size="sm">
                    <DollarSign className="w-3 h-3 mr-1" />
                    {MONETIZATION_LABELS[ip.monetization_model] || ip.monetization_model}
                  </Badge>
                  {ip.content_direction && (
                    <Badge variant="default" size="sm" className="ml-2">
                      <Target className="w-3 h-3 mr-1" />
                      {ip.content_direction}
                    </Badge>
                  )}
                </div>
              )}

              {/* Stats */}
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="p-3 rounded-lg bg-background-tertiary">
                  <div className="flex items-center gap-1.5 text-foreground-tertiary mb-1">
                    <FileText className="w-3.5 h-3.5" />
                    <span className="text-2xs">内容</span>
                  </div>
                  <p className="text-lg font-semibold text-foreground">{stats.content}</p>
                </div>
                <div className="p-3 rounded-lg bg-background-tertiary">
                  <div className="flex items-center gap-1.5 text-foreground-tertiary mb-1">
                    <Users className="w-3.5 h-3.5" />
                    <span className="text-2xs">素材</span>
                  </div>
                  <p className="text-lg font-semibold text-foreground">{stats.assets}</p>
                </div>
                <div className="p-3 rounded-lg bg-background-tertiary">
                  <div className="flex items-center gap-1.5 text-foreground-tertiary mb-1">
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span className="text-2xs">活跃</span>
                  </div>
                  <p className="text-sm font-medium text-foreground">{stats.lastActive}</p>
                </div>
              </div>

              {/* 超级符号完善度 */}
              {ip.nickname && ip.bio && (
                <div className="mb-4 p-2 bg-accent-green/10 border border-accent-green/20 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-accent-green" />
                    <span className="text-xs text-accent-green">超级符号识别系统已配置</span>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-2">
                <Link href={`/ip/${ip.ip_id}`} className="flex-1">
                  <Button variant="secondary" size="sm" className="w-full">
                    详情
                  </Button>
                </Link>
                <Link href={`/agents/memory?ip=${ip.ip_id}`}>
                  <Button variant="ghost" size="sm">
                    素材
                  </Button>
                </Link>
                <Link href={`/config?ip=${ip.ip_id}`}>
                  <Button variant="ghost" size="sm">
                    配置
                  </Button>
                </Link>
              </div>
            </Card>
          );
        })}
      </div>
      )}

      {/* Empty state */}
      {!loading && filteredIPs.length === 0 && (
        <div className="text-center py-16">
          <div className="w-16 h-16 rounded-full bg-background-tertiary flex items-center justify-center mx-auto mb-4">
            <Users className="w-8 h-8 text-foreground-tertiary" />
          </div>
          <h3 className="text-lg font-medium text-foreground mb-2">暂无IP</h3>
          <p className="text-sm text-foreground-secondary mb-4">
            使用专业的IP创建向导，基于账号体系建立你的第一个IP
          </p>
          <Button onClick={() => setShowCreateWizard(true)} leftIcon={<Plus className="w-4 h-4" />}>
            新建IP
          </Button>
        </div>
      )}

      {/* Create IP Wizard */}
      {showCreateWizard && (
        <IPCreationWizard
          onComplete={handleCreateIP}
          onCancel={() => setShowCreateWizard(false)}
          isLoading={creating}
        />
      )}
    </MainLayout>
  );
}
