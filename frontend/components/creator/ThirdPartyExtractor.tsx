'use client';

import { useState } from 'react';
import { ExternalLink, Copy, Check, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface ExtractorTool {
  id: string;
  name: string;
  icon: string;
  description: string;
  buildUrl: (url: string) => string;
  features: string[];
}

const EXTRACTOR_TOOLS: ExtractorTool[] = [
  {
    id: 'anytocopy',
    name: 'AnyToCopy',
    icon: '🔍',
    description: '专业文案提取工具，支持抖音、小红书、B站',
    buildUrl: (url) => `https://www.anytocopy.com/extract?url=${encodeURIComponent(url)}`,
    features: ['支持短视频文案', '评论区提取', '免费使用'],
  },
  {
    id: 'douyin-word',
    name: '抖音文案提取',
    icon: '🎵',
    description: '专门针对抖音的文案提取工具',
    buildUrl: (url) => `https://douyin-tool.com/extract?link=${encodeURIComponent(url)}`,
    features: ['抖音专用', '快速提取', '无需登录'],
  },
  {
    id: 'xhs-copy',
    name: '小红书文案助手',
    icon: '📕',
    description: '小红书笔记文案提取',
    buildUrl: (url) => `https://xhs-extractor.com/?url=${encodeURIComponent(url)}`,
    features: ['小红书专用', '图片文字识别', '标签提取'],
  },
  {
    id: 'copy-tool',
    name: '文案提取神器',
    icon: '✨',
    description: '多平台通用文案提取',
    buildUrl: (url) => `https://copy-tool.com/extract?url=${encodeURIComponent(url)}`,
    features: ['多平台支持', '批量提取', '历史记录'],
  },
];

interface ThirdPartyExtractorProps {
  videoUrl: string;
  onTextExtracted?: (text: string) => void;
}

export function ThirdPartyExtractor({ videoUrl, onTextExtracted }: ThirdPartyExtractorProps) {
  const [copied, setCopied] = useState(false);
  const [manualText, setManualText] = useState('');
  const [showManualInput, setShowManualInput] = useState(false);

  const copyUrl = async () => {
    try {
      await navigator.clipboard.writeText(videoUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  const handleManualSubmit = () => {
    if (manualText.trim() && onTextExtracted) {
      onTextExtracted(manualText.trim());
    }
  };

  return (
    <div className="space-y-4">
      {/* 提示信息 */}
      <div className="p-4 bg-accent-yellow/10 border border-accent-yellow/20 rounded-xl">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-accent-yellow flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-foreground mb-1">
              自动提取暂时不可用
            </p>
            <p className="text-sm text-foreground-secondary">
              你可以使用以下第三方工具提取文案，然后粘贴回来继续仿写。
            </p>
          </div>
        </div>
      </div>

      {/* 视频链接 */}
      <div className="p-3 bg-background-tertiary rounded-lg">
        <p className="text-xs text-foreground-tertiary mb-2">待提取的视频链接：</p>
        <div className="flex items-center gap-2">
          <code className="flex-1 text-xs text-foreground-secondary truncate">
            {videoUrl}
          </code>
          <button
            onClick={copyUrl}
            className="p-2 hover:bg-background-elevated rounded-lg transition-colors"
            title="复制链接"
          >
            {copied ? (
              <Check className="w-4 h-4 text-accent-green" />
            ) : (
              <Copy className="w-4 h-4 text-foreground-secondary" />
            )}
          </button>
        </div>
      </div>

      {/* 第三方工具列表 */}
      <div className="space-y-2">
        <p className="text-sm font-medium text-foreground">推荐工具：</p>
        {EXTRACTOR_TOOLS.map((tool) => (
          <a
            key={tool.id}
            href={tool.buildUrl(videoUrl)}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-start gap-3 p-3 bg-background-tertiary rounded-xl border border-border hover:border-primary-500/50 hover:bg-background-elevated transition-all group"
          >
            <span className="text-2xl">{tool.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-foreground text-sm">
                  {tool.name}
                </span>
                <ExternalLink className="w-3.5 h-3.5 text-foreground-tertiary group-hover:text-primary-400 transition-colors" />
              </div>
              <p className="text-xs text-foreground-secondary mt-0.5">
                {tool.description}
              </p>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {tool.features.map((feature) => (
                  <span
                    key={feature}
                    className="px-2 py-0.5 bg-background-elevated text-foreground-tertiary text-[10px] rounded-full"
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </div>
          </a>
        ))}
      </div>

      {/* 手动输入选项 */}
      <div className="border-t border-border pt-4">
        <button
          onClick={() => setShowManualInput(!showManualInput)}
          className="text-sm text-primary-400 hover:text-primary-300 underline"
        >
          {showManualInput ? '取消手动输入' : '已有文案？直接粘贴 →'}
        </button>

        {showManualInput && (
          <div className="mt-3 space-y-3">
            <textarea
              value={manualText}
              onChange={(e) => setManualText(e.target.value)}
              placeholder="粘贴从第三方工具提取的文案..."
              rows={6}
              className="w-full p-3 bg-background-tertiary border border-border rounded-lg text-foreground placeholder:text-foreground-muted resize-none focus:outline-none focus:border-primary-500/50"
            />
            <Button
              onClick={handleManualSubmit}
              disabled={!manualText.trim()}
              className="w-full"
            >
              使用此文案进行仿写
            </Button>
          </div>
        )}
      </div>

      {/* 使用说明 */}
      <div className="p-3 bg-background-tertiary/50 rounded-lg text-xs text-foreground-secondary space-y-1.5">
        <p className="font-medium text-foreground">💡 使用步骤：</p>
        <ol className="list-decimal list-inside space-y-1 ml-1">
          <li>点击上方任意工具打开提取页面</li>
          <li>等待工具提取文案（通常几秒）</li>
          <li>复制提取的文案</li>
          <li>返回本页面点击「直接粘贴」</li>
          <li>粘贴文案并点击「使用此文案进行仿写」</li>
        </ol>
      </div>
    </div>
  );
}
