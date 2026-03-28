'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { 
  Loader2, 
  RefreshCw,
  Brain,
  Sparkles,
  Search,
  Layers,
  Database,
  FileText,
  PenTool,
  Upload
} from 'lucide-react';
import { api } from '@/lib/api';
import { IP } from '@/types';
import { MemorySearchPanel, MemoryConsolidationPanel, MultimodalPanel, ContentGeneratorPanel, UploadPanel } from '../components';

export default function IPDetailPage() {
  const params = useParams();
  const ipId = params?.id as string;
  
  const [ip, setIp] = useState<IP | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<any>(null);
  const [assetsRefreshKey, setAssetsRefreshKey] = useState(0);

  const refreshAssetsList = useCallback(() => {
    setAssetsRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    if (ipId) {
      loadIP();
    }
  }, [ipId]);

  const loadIP = async () => {
    setLoading(true);
    try {
      const data = await api.getIP(ipId);
      setIp(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const result = await api.syncFeishu(ipId);
      setSyncResult(result);
    } catch (e) {
      console.error(e);
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <MainLayout title="加载中...">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      </MainLayout>
    );
  }

  if (!ip) {
    return (
      <MainLayout title="IP不存在">
        <div className="text-center py-12">
          <p className="text-gray-500">IP不存在</p>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout title={ip.name}>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">{ip.name}</h1>
            <p className="text-gray-500 font-mono text-sm">{ip.ip_id}</p>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              onClick={handleSync}
              disabled={syncing}
            >
              {syncing ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <RefreshCw className="w-4 h-4 mr-2" />
              )}
              同步知识库
            </Button>
          </div>
        </div>
        
        {/* 同步结果提示 */}
        {syncResult && (
          <div className={`mt-3 p-3 rounded-lg text-sm ${
            syncResult.synced > 0 ? 'bg-green-50 text-green-700' : 'bg-gray-50 text-gray-600'
          }`}>
            同步完成：新增/更新 {syncResult.synced} 条，跳过 {syncResult.skipped || 0} 条
            {syncResult.deleted > 0 && `，删除 ${syncResult.deleted} 条`}
          </div>
        )}
      </div>

      {/* Tabs */}
      <Tabs defaultValue="memory" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="memory">
            <Brain className="w-4 h-4 mr-2" />
            记忆检索
          </TabsTrigger>
          <TabsTrigger value="consolidation">
            <Layers className="w-4 h-4 mr-2" />
            记忆管理
          </TabsTrigger>
          <TabsTrigger value="multimodal">
            <Sparkles className="w-4 h-4 mr-2" />
            多模态
          </TabsTrigger>
          <TabsTrigger value="content">
            <PenTool className="w-4 h-4 mr-2" />
            内容生成
          </TabsTrigger>
          <TabsTrigger value="upload">
            <Upload className="w-4 h-4 mr-2" />
            本地上传
          </TabsTrigger>
          <TabsTrigger value="assets">
            <FileText className="w-4 h-4 mr-2" />
            素材库
          </TabsTrigger>
        </TabsList>

        {/* 记忆检索 */}
        <TabsContent value="memory">
          <MemorySearchPanel ipId={ipId} />
        </TabsContent>

        {/* 记忆管理 */}
        <TabsContent value="consolidation">
          <MemoryConsolidationPanel ipId={ipId} />
        </TabsContent>

        {/* 多模态 */}
        <TabsContent value="multimodal">
          <MultimodalPanel ipId={ipId} />
        </TabsContent>

        {/* 内容生成 */}
        <TabsContent value="content">
          <ContentGeneratorPanel ipId={ipId} />
        </TabsContent>

        {/* 本地上传 */}
        <TabsContent value="upload">
          <UploadPanel ipId={ipId} onUploadComplete={refreshAssetsList} />
        </TabsContent>

        {/* 素材库 */}
        <TabsContent value="assets">
          <AssetsPanel ipId={ipId} refreshKey={assetsRefreshKey} />
        </TabsContent>
      </Tabs>
    </MainLayout>
  );
}

// 素材库组件
function AssetsPanel({ ipId, refreshKey }: { ipId: string; refreshKey: number }) {
  const [assets, setAssets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  const loadAssets = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getAssets(ipId, 20, 0);
      setAssets(data.items || []);
      setTotal(data.total || 0);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [ipId]);

  useEffect(() => {
    loadAssets();
  }, [loadAssets, refreshKey]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">素材列表</h3>
        <Badge variant="outline">共 {total} 条</Badge>
      </div>
      
      <div className="space-y-2">
        {assets.map((asset) => (
          <div key={asset.asset_id} className="p-3 border rounded-lg">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <div className="font-medium text-sm">{asset.title || asset.asset_id}</div>
                <p className="text-gray-500 text-xs mt-1 line-clamp-2">
                  {asset.content_snippet}
                </p>
              </div>
              <Badge variant="outline" className="text-xs">
                {asset.asset_type}
              </Badge>
            </div>
          </div>
        ))}
        
        {assets.length === 0 && (
          <div className="text-center py-8 text-gray-400">
            暂无素材，请先同步知识库
          </div>
        )}
      </div>
    </Card>
  );
}
