'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { 
  Image as ImageIcon, 
  Video, 
  Music, 
  Loader2, 
  Send,
  Sparkles,
  Upload,
  FileText
} from 'lucide-react';
import { api } from '@/lib/api';

interface MultimodalPanelProps {
  ipId: string;
}

type Mode = 'image' | 'video' | 'audio';

export function MultimodalPanel({ ipId }: MultimodalPanelProps) {
  const [mode, setMode] = useState<Mode>('image');
  const [url, setUrl] = useState('');
  const [prompt, setPrompt] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [creatingAsset, setCreatingAsset] = useState(false);

  const handleAnalyze = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setResult(null);

    try {
      let data;
      if (mode === 'image') {
        data = await api.analyzeImage(url, prompt || undefined);
      } else if (mode === 'video') {
        data = await api.analyzeVideo(url, prompt || undefined);
      } else {
        data = await api.extractAudioTopics(url, 5);
      }
      setResult(data);
    } catch (e) {
      console.error(e);
      setResult({ error: (e as Error).message });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAsset = async () => {
    if (!url.trim()) return;
    setCreatingAsset(true);

    try {
      await api.createMultimodalAsset({
        ip_id: ipId,
        source_type: mode,
        source_url: url,
        content: result?.analysis || result?.raw_analysis || '',
        title: `${mode}素材`,
      });
      alert('素材创建成功！');
    } catch (e) {
      console.error(e);
      alert('创建失败: ' + (e as Error).message);
    } finally {
      setCreatingAsset(false);
    }
  };

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-orange-500" />
          <h3 className="font-semibold">多模态理解</h3>
        </div>
      </div>

      {/* 模式选择 */}
      <div className="flex gap-2 mb-4">
        <Button
          variant={mode === 'image' ? 'primary' : 'outline'}
          size="sm"
          onClick={() => setMode('image')}
        >
          <FileText className="w-4 h-4 mr-1" />
          图片
        </Button>
        <Button
          variant={mode === 'video' ? 'primary' : 'outline'}
          size="sm"
          onClick={() => setMode('video')}
        >
          <FileText className="w-4 h-4 mr-1" />
          视频
        </Button>
        <Button
          variant={mode === 'audio' ? 'primary' : 'outline'}
          size="sm"
          onClick={() => setMode('audio')}
        >
          <FileText className="w-4 h-4 mr-1" />
          音频
        </Button>
      </div>

      {/* URL输入 */}
      <div className="mb-3">
        <Input
          placeholder={
            mode === 'image' ? '输入图片URL...' :
            mode === 'video' ? '输入视频URL...' :
            '输入音频转写文本...'
          }
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
      </div>

      {/* Prompt输入 */}
      {mode !== 'audio' && (
        <div className="mb-3">
          <Input
            placeholder="自定义分析提示词（可选）"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </div>
      )}

      {/* 分析按钮 */}
      <Button 
        onClick={handleAnalyze} 
        disabled={loading || !url.trim()}
        className="w-full mb-4"
      >
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin mr-2" />
        ) : (
          mode === 'image' ? <ImageIcon className="w-4 h-4 mr-2" /> :
          mode === 'video' ? <Video className="w-4 h-4 mr-2" /> :
          <Music className="w-4 h-4 mr-2" />
        )}
        {mode === 'image' ? '分析图片' : mode === 'video' ? '分析视频' : '提取主题'}
      </Button>

      {/* 结果展示 */}
      {result && (
        <div className="border-t pt-4">
          {result.error ? (
            <div className="p-3 bg-red-50 rounded-lg text-sm text-red-600">
              {result.error}
            </div>
          ) : (
            <>
              {/* 分析结果 */}
              <div className="mb-3">
                <div className="text-sm font-medium mb-2">分析结果</div>
                <div className="p-3 bg-gray-50 rounded-lg text-sm whitespace-pre-wrap">
                  {result.analysis || result.raw_analysis || JSON.stringify(result, null, 2)}
                </div>
              </div>

              {/* 主题标签 */}
              {result.topics && (
                <div className="mb-3">
                  <div className="text-sm font-medium mb-2">主题标签</div>
                  <div className="flex flex-wrap gap-1">
                    {result.topics.map((topic: string, idx: number) => (
                      <Badge key={idx} variant="outline">{topic}</Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* 情感倾向 */}
              {result.sentiment && (
                <div className="mb-3">
                  <div className="text-sm font-medium mb-2">情感倾向</div>
                  <Badge variant={result.sentiment === 'positive' ? 'success' : 
                    result.sentiment === 'negative' ? 'danger' : 'outline'}>
                    {result.sentiment === 'positive' ? '正面' : 
                     result.sentiment === 'negative' ? '负面' : '中性'}
                  </Badge>
                </div>
              )}

              {/* 创建素材按钮 */}
              <Button
                variant="outline"
                size="sm"
                onClick={handleCreateAsset}
                disabled={creatingAsset}
                className="w-full"
              >
                {creatingAsset ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Upload className="w-4 h-4 mr-2" />
                )}
                存为素材
              </Button>
            </>
          )}
        </div>
      )}
    </Card>
  );
}
