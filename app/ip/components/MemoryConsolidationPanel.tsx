'use client';

// Icons from lucide-react
import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { 
  RefreshCw, 
  Loader2, 
  Brain, 
 
  Star,
  TrendingUp,
  Clock,
  RotateCcw
} from 'lucide-react';
import { api } from '@/lib/api';
import type { MemorySummaryResult, CoreMemoryResult, MemoryConsolidateResult } from '@/types';

interface MemoryConsolidationPanelProps {
  ipId: string;
}

export function MemoryConsolidationPanel({ ipId }: MemoryConsolidationPanelProps) {
  const [summary, setSummary] = useState<MemorySummaryResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [consolidating, setConsolidating] = useState(false);
  const [activeTab, setActiveTab] = useState<'summary' | 'core' | 'archived'>('summary');

  useEffect(() => {
    loadSummary();
  }, [ipId]);

  const loadSummary = async () => {
    setLoading(true);
    try {
      const data = await api.getMemorySummary(ipId);
      setSummary(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleConsolidate = async () => {
    setConsolidating(true);
    try {
      await api.consolidateMemory(ipId);
      await loadSummary();
    } catch (e) {
      console.error(e);
    } finally {
      setConsolidating(false);
    }
  };

  const handleRestore = async (assetId: string) => {
    try {
      await api.restoreFromArchive(ipId, assetId);
      await loadSummary();
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) {
    return (
      <Card className="p-4">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      </Card>
    );
  }

  const stats = summary?.stats || { total: 0, by_level: {}, avg_usage: 0 };

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-blue-500" />
          <h3 className="font-semibold">记忆管理</h3>
        </div>
        <Button 
          size="sm" 
          variant="outline"
          onClick={handleConsolidate}
          disabled={consolidating}
        >
          {consolidating ? (
            <Loader2 className="w-4 h-4 animate-spin mr-1" />
          ) : (
            <RefreshCw className="w-4 h-4 mr-1" />
          )}
          整理记忆
        </Button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="p-3 bg-red-50 rounded-lg text-center">
          <Star className="w-5 h-5 text-red-500 mx-auto mb-1" />
          <div className="text-lg font-bold text-red-600">
            {stats.by_level?.core || 0}
          </div>
          <div className="text-xs text-gray-500">核心记忆</div>
        </div>
        <div className="p-3 bg-yellow-50 rounded-lg text-center">
          <TrendingUp className="w-5 h-5 text-yellow-500 mx-auto mb-1" />
          <div className="text-lg font-bold text-yellow-600">
            {stats.by_level?.active || 0}
          </div>
          <div className="text-xs text-gray-500">活跃记忆</div>
        </div>
        <div className="p-3 bg-gray-50 rounded-lg text-center">
          <Star className="w-5 h-5 text-gray-500 mx-auto mb-1" />
          <div className="text-lg font-bold text-gray-600">
            {stats.by_level?.archive || 0}
          </div>
          <div className="text-xs text-gray-500">归档记忆</div>
        </div>
      </div>

      {/* 核心摘要 */}
      {summary?.stats?.total !== undefined && summary.stats.total > 0 && (
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Button
              variant={activeTab === 'summary' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setActiveTab('summary')}
            >
              摘要
            </Button>
            <Button
              variant={activeTab === 'core' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setActiveTab('core')}
            >
              核心 ({summary.core_memory?.length || 0})
            </Button>
            <Button
              variant={activeTab === 'archived' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setActiveTab('archived')}
            >
              归档 ({summary.archived_memory?.length || 0})
            </Button>
          </div>

          {activeTab === 'summary' && summary.stats.total > 0 && (
            <div className="p-3 bg-blue-50 rounded-lg text-sm text-gray-700">
              <div className="font-medium mb-1">记忆统计</div>
              <div>总素材: {stats.total} | 平均使用: {stats.avg_usage.toFixed(1)}次</div>
            </div>
          )}

          {activeTab === 'core' && (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {summary.core_memory?.map((item) => (
                <div key={item.asset_id} className="p-2 border rounded text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{item.title}</span>
                    <Badge variant="outline">{item.usage_count}次</Badge>
                  </div>
                  <p className="text-gray-500 text-xs mt-1 line-clamp-2">
                    {item.content_snippet}
                  </p>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'archived' && (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {summary.archived_memory?.map((item) => (
                <div key={item.asset_id} className="p-2 border rounded text-sm opacity-75">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{item.title}</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleRestore(item.asset_id)}
                    >
                      <RotateCcw className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              ))}
              {(!summary.archived_memory || summary.archived_memory.length === 0) && (
                <div className="text-center py-4 text-gray-400 text-sm">
                  暂无归档记忆
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {summary?.stats?.total === 0 && (
        <div className="text-center py-4 text-gray-400 text-sm">
          暂无记忆数据，请先同步知识库
        </div>
      )}
    </Card>
  );
}
