'use client';

import { cn } from '@/lib/utils';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Users, 
  Brain, 
  GitBranch, 
  FileText, 
  Shield, 
  Video, 
  BarChart3, 
  Settings,
  Cloud,
  Sparkles,
  PenTool,
  LogIn,
} from 'lucide-react';

const navigation = [
  { name: '仪表盘', href: '/', icon: LayoutDashboard },
  { name: 'IP管理', href: '/ip', icon: Users },
  { 
    name: '7-Agent工作流', 
    href: '/agents', 
    icon: Sparkles,
    children: [
      { name: '记忆Agent', href: '/agents/memory', icon: Brain },
      { name: '策略Agent', href: '/agents/strategy', icon: GitBranch },
      { name: '重组Agent', href: '/agents/remix', icon: FileText },
      { name: '生成Agent', href: '/agents/generation', icon: FileText },
      { name: '合规Agent', href: '/agents/compliance', icon: Shield },
      { name: '视觉Agent', href: '/agents/visual', icon: Video },
      { name: '分析Agent', href: '/agents/analytics', icon: BarChart3 },
    ]
  },
  { 
    name: '配置中心', 
    href: '/config', 
    icon: Settings,
    children: [
      { name: '通用设置', href: '/config', icon: Settings },
      { name: '集成配置', href: '/config/integrations', icon: Cloud },
    ]
  },
  { 
    name: 'IP创作端', 
    href: '/creator/dashboard', 
    icon: PenTool,
    external: true
  },
];

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        'w-64 max-w-[16rem] h-screen overflow-x-hidden',
        'bg-background-secondary border-r border-border',
        'flex flex-col',
        'fixed left-0 top-0 z-40',
        className
      )}
    >
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-border">
        <Link href="/" className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-cyan flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-foreground">AI-Native IP</h1>
            <p className="text-2xs text-foreground-tertiary">工厂 · Factory</p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        <ul className="space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
            
            const linkContent = (
              <>
                <Icon className={cn('w-4 h-4', isActive && 'text-primary-400')} />
                {item.name}
                {item.external && (
                  <span className="ml-auto text-xs text-foreground-muted">→</span>
                )}
              </>
            );
            
            return (
              <li key={item.name}>
                {item.external ? (
                  <a
                    href={item.href}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2.5 rounded-xl',
                      'text-sm font-medium transition-all duration-200',
                      'text-foreground-secondary hover:text-foreground hover:bg-background-tertiary'
                    )}
                  >
                    {linkContent}
                  </a>
                ) : (
                  <Link
                    href={item.href}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2.5 rounded-xl',
                      'text-sm font-medium transition-all duration-200',
                      isActive
                        ? 'bg-primary-500/10 text-primary-400'
                        : 'text-foreground-secondary hover:text-foreground hover:bg-background-tertiary'
                    )}
                  >
                    {linkContent}
                  </Link>
                )}
                
                {/* Sub-items */}
                {item.children && isActive && (
                  <ul className="mt-1 ml-4 pl-4 border-l border-border space-y-1">
                    {item.children.map((child) => {
                      const ChildIcon = child.icon;
                      const isChildActive = pathname === child.href;
                      
                      return (
                        <li key={child.name}>
                          <Link
                            href={child.href}
                            className={cn(
                              'flex items-center gap-3 px-3 py-2 rounded-lg',
                              'text-sm transition-all duration-200',
                              isChildActive
                                ? 'text-primary-400'
                                : 'text-foreground-tertiary hover:text-foreground-secondary'
                            )}
                          >
                            <ChildIcon className="w-3.5 h-3.5" />
                            {child.name}
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border space-y-3">
        <Link
          href="/login"
          className={cn(
            'flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium',
            'text-foreground-secondary hover:text-foreground hover:bg-background-tertiary transition-colors'
          )}
        >
          <LogIn className="w-4 h-4" />
          登录 / 验证码
        </Link>
        <div className="bg-gradient-to-r from-primary-500/10 to-accent-cyan/10 rounded-xl p-4">
          <p className="text-xs font-medium text-foreground mb-1">系统状态</p>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
            <span className="text-2xs text-foreground-secondary">所有Agent运行正常</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
