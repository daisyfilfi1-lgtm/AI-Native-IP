'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { 
  Search, 
  Loader2, 
  FileText, 
  GitBranch, 
  Layers,
  Zap,
  Brain,
  Image as ImageIcon,
  Video,
  Music,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Clock
} from 'lucide-react';
import { api } from '@/lib/api';
import type { HybridRetrieveResult, CoreMemoryResult, MemorySummaryResult } from '@/types';

interface MemorySearchPanelProps {
  ipId: string;
}

export function MemorySearchPanel({ ipId }: MemorySearchPanelProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchType, setSearchType] = useState<'hybrid' | 'vector' | 'graph'>('hybrid');
  const [vectorWeight, setVectorWeight] = useState(0.6);
  const [graphWeight, setGraphWeight] = useState(0.4);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    
    try {
      if (searchType === 'hybrid') {
        const data = await api.hybridRetrieve({
          ip_id: ipId,
          query,
          vector_weight: vectorWeight,
          graph_weight: graphWeight,
          top_k: 10,
        });
        setResults(data.results);
      } else if (searchType === 'vector') {
        const data = await api.vectorSearch(ipId, query);
        setResults(data.results || []);
      } else {
        const data = await api.retrieveGraph({
          ip_id: ipId,
          query,
          depth: 2,
          limit: 10,
        });
        setResults(data.paths || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-4">
      <div className="flex items-center gap-2 mb-4">
        <Brain className="w-5 h-5 text-purple-500" />
        <h3 className="font-semibold">记忆检索</h3>
        <Badge variant="outline" className="ml-auto">
          {searchType === 'hybrid' ? '混合检索' : searchType === 'vector' ? '向量检索' : '图检索'}
        </Badge>
      </div>

      {/* 搜索类型选择 */}
      <div className="flex gap-2 mb-4">
        {(['hybrid', 'vector', 'graph'] as const).map((type) => (
          <Button
            key={type}
            variant={searchType === type ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setSearchType(type)}
          >
            {type === 'hybrid' && <Layers className="w-4 h-4 mr-1" />}
            {type === 'vector' && <Zap className="w-4 h-4 mr-1" />}
            {type === 'graph' && <GitBranch className="w-4 h-4 mr-1" />}
            {type === 'hybrid' ? '混合' : type === 'vector' ? '向量' : '图谱'}
          </Button>
        ))}
      </div>

      {/* 混合检索权重滑块 */}
      {searchType === 'hybrid' && (
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <label className="text-sm text-gray-600 mb-2 block">
            向量权重: {vectorWeight} | 图谱权重: {graphWeight}
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={vectorWeight}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              setVectorWeight(v);
              setGraphWeight(1 - v);
            }}
            className="w-full"
          />
        </div>
      )}

      {/* 搜索输入 */}
      <div className="flex gap-2 mb-4">
        <Input
          placeholder="输入关键词搜索记忆..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <Button onClick={handleSearch} disabled={loading}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
        </Button>
      </div>

      {/* 结果展示 */}
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {results.map((result, idx) => (
          <div key={idx} className="p-3 border rounded-lg hover:bg-gray-50 transition-colors">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-sm">
                    {result.title || result.asset_id || result.from}
                  </span>
                  {result.sources && result.sources.map((s: string) => (
                    <Badge key={s} variant="outline" className="text-xs">
                      {s}
                    </Badge>
                  ))}
                </div>
                <p className="text-sm text-gray-600 line-clamp-2">
                  {result.content_snippet || result.content || result.context || ''}
                </p>
              </div>
              <span className="text-xs text-gray-400">
                {(result.hybrid_score || result.similarity || result.score || 0).toFixed(2)}
              </span>
            </div>
          </div>
        ))}
        
        {!loading && results.length === 0 && query && (
          <div className="text-center py-8 text-gray-400">
            未找到相关记忆
          </div>
        )}
      </div>
    </Card>
  );
}
