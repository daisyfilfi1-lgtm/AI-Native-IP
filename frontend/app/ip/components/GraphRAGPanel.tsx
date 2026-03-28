'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import {
  GitBranch,
  Loader2,
  Search,
  Plus,
  Trash2,
  Database,
  ArrowRight,
} from 'lucide-react';
import { api } from '@/lib/api';
import type { GraphStatsResult, GraphRetrieveResult } from '@/types';

interface GraphRAGPanelProps {
  ipId: string;
}

export function GraphRAGPanel({ ipId }: GraphRAGPanelProps) {
  const [stats, setStats] = useState<GraphStatsResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [building, setBuilding] = useState(false);
  const [query, setQuery] = useState('');
  const [graphResults, setGraphResults] = useState<GraphRetrieveResult | null>(null);
  const [searching, setSearching] = useState(false);

  const loadStats = async () => {
    setLoading(true);
    try {
      const data = await api.getGraphStats(ipId);
      setStats(data);
    } catch (e) {
      console.error(e);
      setStats(null);
    } finally {
      setLoading(false);
    }
  };

  const handleBuild = async () => {
    setBuilding(true);
    try {
      await api.buildGraph({ ip_id: ipId, force_rebuild: false });
      await loadStats();
    } catch (e) {
      console.error(e);
    } finally {
      setBuilding(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('确定要删除知识图谱吗？此操作不可恢复。')) return;
    try {
      await api.deleteGraph(ipId);
      setStats(null);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const data = await api.retrieveGraph({
        ip_id: ipId,
        query,
        depth: 2,
        limit: 10,
      });
      setGraphResults(data);
    } catch (e) {
      console.error(e);
    } finally {
      setSearching(false);
    }
  };

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-green-500" />
          <h3 className="font-semibold">知识图谱</h3>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={loadStats} disabled={loading}>
            刷新
          </Button>
          <Button size="sm" variant="outline" onClick={handleDelete} disabled={!stats}>
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* 图谱统计 */}
      <div className="mb-4">
        {loading ? (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
          </div>
        ) : stats ? (
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-green-50 rounded-lg text-center">
              <GitBranch className="w-5 h-5 text-green-500 mx-auto mb-1" />
              <div className="text-lg font-bold text-green-600">
                {stats.total_nodes}
              </div>
              <div className="text-xs text-gray-500">实体数</div>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg text-center">
              <ArrowRight className="w-5 h-5 text-blue-500 mx-auto mb-1" />
              <div className="text-lg font-bold text-blue-600">
                {stats.total_relations}
              </div>
              <div className="text-xs text-gray-500">关系数</div>
            </div>
          </div>
        ) : (
          <div className="text-center py-4">
            <Database className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p className="text-sm text-gray-400 mb-3">知识图谱未构建</p>
            <Button size="sm" onClick={handleBuild} disabled={building}>
              {building ? (
                <Loader2 className="w-4 h-4 animate-spin mr-1" />
              ) : (
                <Plus className="w-4 h-4 mr-1" />
              )}
              构建图谱
            </Button>
          </div>
        )}
      </div>

      {/* 实体类型分布 */}
      {stats && stats.nodes && Object.keys(stats.nodes).length > 0 && (
        <div className="mb-4">
          <div className="text-sm font-medium mb-2">实体类型</div>
          <div className="flex flex-wrap gap-1">
            {Object.entries(stats.nodes).map(([type, count]) => (
              <Badge key={type} variant="outline" className="text-xs">
                {type}: {count}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* 图检索 */}
      {stats && (
        <div className="border-t pt-4">
          <div className="text-sm font-medium mb-2">图谱检索</div>
          <div className="flex gap-2 mb-3">
            <Input
              placeholder="输入查询..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
            <Button onClick={handleSearch} disabled={searching}>
              {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            </Button>
          </div>

          {/* 检索结果 */}
          {graphResults && graphResults.paths && graphResults.paths.length > 0 && (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              <div className="text-xs text-gray-500 mb-2">
                找到 {graphResults.paths.length} 条关系
              </div>
              {graphResults.paths.map((path, idx) => (
                <div key={idx} className="p-2 border rounded text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{path.from}</span>
                    <Badge variant="outline" className="text-xs">{path.relation}</Badge>
                    <span className="font-medium">{path.to}</span>
                  </div>
                  {path.context && (
                    <p className="text-xs text-gray-500 mt-1">{path.context}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {graphResults && (!graphResults.paths || graphResults.paths.length === 0) && (
            <div className="text-center py-2 text-gray-400 text-sm">
              未找到相关关系
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
