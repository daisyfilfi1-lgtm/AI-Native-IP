'use client';

import { useState, useRef } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Loader2, Upload, FileText, File, Check, X } from 'lucide-react';
import { api } from '@/lib/api';

interface UploadPanelProps {
  ipId: string;
  onUploadComplete?: () => void;
}

export function UploadPanel({ ipId, onUploadComplete }: UploadPanelProps) {
  const [uploading, setUploading] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  /** 已成功上传的文件名（与 files 对应展示勾选） */
  const [uploadedNames, setUploadedNames] = useState<string[]>([]);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
      setUploadedNames([]);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    
    setUploading(true);
    setError('');
    const names: string[] = [];
    const failedFiles: string[] = [];

    for (const file of files) {
      try {
        // 1. 上传文件
        const uploadResult = await api.uploadMemoryFile(ipId, file);
        
        // 2. 创建录入任务（关键！之前缺少这步导致400错误）
        const fileExtension = file.name.split('.').pop()?.toLowerCase() || '';
        const sourceType = ['mp4', 'avi', 'mov', 'webm'].includes(fileExtension) ? 'video' :
                          ['mp3', 'wav', 'ogg', 'm4a'].includes(fileExtension) ? 'audio' :
                          'document';
        
        await api.ingestMemory({
          ip_id: ipId,
          source_type: sourceType,
          local_file_id: uploadResult.file_id,
          title: file.name,
        });
        
        names.push(file.name);
      } catch (e: any) {
        console.error(`上传/录入失败: ${file.name}`, e);
        failedFiles.push(file.name);
        
        // 显示详细错误信息
        const errorMsg = e?.response?.data?.detail || e?.message || '未知错误';
        setError(`${file.name}: ${errorMsg}`);
      }
    }

    setUploadedNames(names);
    setUploading(false);
    
    // 只有全部成功才调用 onUploadComplete
    if (names.length > 0 && failedFiles.length === 0 && onUploadComplete) {
      onUploadComplete();
    }
    
    // 如果有部分失败，显示汇总
    if (failedFiles.length > 0 && failedFiles.length !== files.length) {
      setError(`${failedFiles.length} 个文件处理失败，${names.length} 个成功`);
    }
  };

  const handleRemove = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  return (
    <Card className="p-4">
      <div className="flex items-center gap-2 mb-4">
        <Upload className="w-5 h-5 text-blue-500" />
        <h3 className="font-semibold">本地上传</h3>
      </div>
      
      {/* 文件选择 */}
      <div 
        className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer hover:border-gray-400 transition-colors"
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".txt,.md,.doc,.docx,.pdf"
          onChange={handleFileSelect}
          className="hidden"
        />
        <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
        <p className="text-sm text-gray-500">
          点击选择文件，或拖拽到此处
        </p>
        <p className="text-xs text-gray-400 mt-1">
          支持 txt, md, doc, docx, pdf
        </p>
      </div>
      
      {/* 文件列表 */}
      {files.length > 0 && (
        <div className="mt-4 space-y-2">
          {files.map((file, index) => (
            <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-gray-500" />
                <span className="text-sm truncate max-w-[200px]">{file.name}</span>
                <Badge variant="outline" className="text-xs">
                  {(file.size / 1024).toFixed(1)} KB
                </Badge>
              </div>
              {uploadedNames.includes(file.name) ? (
                <Check className="w-4 h-4 text-green-500" />
              ) : (
                <button onClick={() => handleRemove(index)} className="text-gray-400 hover:text-red-500">
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
      
      {/* 错误提示 */}
      {error && (
        <div className="mt-3 p-2 bg-red-50 text-red-600 text-sm rounded">
          {error}
        </div>
      )}
      
      {/* 上传按钮 */}
      {files.length > 0 && (
        <Button 
          onClick={handleUpload}
          disabled={uploading || uploadedNames.length === files.length}
          className="w-full mt-4"
        >
          {uploading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              上传中...
            </>
          ) : (
            <>
              <Upload className="w-4 h-4 mr-2" />
              上传 {files.length} 个文件
            </>
          )}
        </Button>
      )}
      
      {/* 上传成功 */}
      {uploadedNames.length > 0 && uploadedNames.length === files.length && (
        <div className="mt-3 p-2 bg-green-50 text-green-600 text-sm rounded flex items-center gap-2">
          <Check className="w-4 h-4" />
          上传成功！
        </div>
      )}
    </Card>
  );
}
