'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { creatorApi } from '@/lib/api/creator';
import { 
  MessageCircle, 
  X,
  AlertCircle,
  FileText,
  User,
  Sparkles,
  HelpCircle
} from 'lucide-react';

interface RewriteFeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  draftId: string;
  ipId: string;
  onConfirm: (reason: string, comment: string) => void;
  isLoading?: boolean;
}

// 重写原因选项
const REWRITE_REASONS = [
  { 
    id: 'tag_story', 
    label: '故事/案例不够吸引', 
    icon: FileText,
    description: '案例不够接地气，不够有吸引力'
  },
  { 
    id: 'tag_structure', 
    label: '文章结构有问题', 
    icon: AlertCircle,
    description: '逻辑不清晰，结构混乱'
  },
  { 
    id: 'tag_ip_position', 
    label: '不符合IP人设/语气', 
    icon: User,
    description: '语气不像本人，不够真实'
  },
  { 
    id: 'tag_ai_flavor', 
    label: 'AI味太重', 
    icon: Sparkles,
    description: '读起来不像人话，太生硬'
  },
  { 
    id: 'tag_general', 
    label: '整体不满意', 
    icon: HelpCircle,
    description: '想大改，不知道哪里问题'
  },
];

export function RewriteFeedbackModal({
  isOpen,
  onClose,
  draftId,
  ipId,
  onConfirm,
  isLoading
}: RewriteFeedbackModalProps) {
  const [selectedReason, setSelectedReason] = useState<string>('');
  const [comment, setComment] = useState('');
  const [showComment, setShowComment] = useState(false);

  const handleConfirm = async () => {
    if (!selectedReason) return;
    
    // 提交反馈
    try {
      await creatorApi.submitRewriteFeedback({
        draft_id: draftId,
        ip_id: ipId,
        rewrite_reason: selectedReason,
        user_comment: comment || undefined
      });
    } catch (e) {
      console.error('Failed to submit feedback:', e);
    }
    
    // 触发重写
    onConfirm(selectedReason, comment);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 背景遮罩 */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* 弹窗内容 */}
      <div className="relative bg-background rounded-xl shadow-2xl w-full max-w-md mx-4 p-6">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-lg hover:bg-background-tertiary transition-colors"
        >
          <X className="w-5 h-5 text-foreground-secondary" />
        </button>
        
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-accent-primary/10">
            <MessageCircle className="w-5 h-5 text-accent-primary" />
          </div>
          <h3 className="text-lg font-semibold text-foreground">
            为什么想重写？
          </h3>
        </div>
        
        <p className="text-sm text-foreground-secondary mb-4">
          您的反馈会帮助AI越学越聪明
        </p>
        
        {/* 原因选项 */}
        <div className="space-y-2 mb-4">
          {REWRITE_REASONS.map((reason) => {
            const Icon = reason.icon;
            const isSelected = selectedReason === reason.id;
            
            return (
              <button
                key={reason.id}
                onClick={() => {
                  setSelectedReason(reason.id);
                  setShowComment(true);
                }}
                className={`w-full p-3 rounded-lg border text-left transition-all ${
                  isSelected 
                    ? 'border-accent-primary bg-accent-primary/10' 
                    : 'border-border hover:border-foreground-tertiary hover:bg-background-tertiary'
                }`}
              >
                <div className="flex items-start gap-3">
                  <Icon className={`w-5 h-5 mt-0.5 ${isSelected ? 'text-accent-primary' : 'text-foreground-secondary'}`} />
                  <div>
                    <div className={`font-medium ${isSelected ? 'text-accent-primary' : 'text-foreground'}`}>
                      {reason.label}
                    </div>
                    <div className="text-xs text-foreground-secondary">
                      {reason.description}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
        
        {/* 补充说明（可选） */}
        {showComment && (
          <div className="mb-4 animate-in fade-in slide-in-from-top-2 duration-200">
            <Textarea
              placeholder="还想说点什么？（可选）"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="min-h-[80px] resize-none"
            />
          </div>
        )}
        
        {/* 按钮 */}
        <div className="flex gap-3">
          <Button
            variant="secondary"
            onClick={onClose}
            className="flex-1"
            disabled={isLoading}
          >
            取消
          </Button>
          <Button
            onClick={handleConfirm}
            className="flex-1"
            disabled={!selectedReason || isLoading}
            isLoading={isLoading}
          >
            确认重写
          </Button>
        </div>
      </div>
    </div>
  );
}
