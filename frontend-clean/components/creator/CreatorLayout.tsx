'use client';

import { cn } from '@/lib/utils';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Sparkles, 
  Library, 
  BarChart3,
  User,
  Settings,
  LogOut
} from 'lucide-react';

const navigation = [
  { name: '今日工作台', href: '/creator/dashboard', icon: LayoutDashboard },
  { name: '魔法生成', href: '/creator/generate', icon: Sparkles },
  { name: '我的内容库', href: '/creator/library', icon: Library },
  { name: '我的数据', href: '/creator/analytics', icon: BarChart3 },
];

interface CreatorLayoutProps {
  children: React.ReactNode;
}

export function CreatorLayout({ children }: CreatorLayoutProps) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-background">
      {/* Top Navigation */}
      <header className="fixed top-0 left-0 right-0 h-16 bg-background/80 backdrop-blur-xl border-b border-border z-50">
        <div className="h-full px-4 lg:px-6 flex items-center justify-between">
          {/* Logo */}
          <Link href="/creator/dashboard" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-cyan flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-foreground">IP创作助手</span>
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
              
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-primary-500/10 text-primary-400'
                      : 'text-foreground-secondary hover:text-foreground hover:bg-background-tertiary'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* User Actions */}
          <div className="flex items-center gap-2">
            <button className="p-2 rounded-lg text-foreground-secondary hover:text-foreground hover:bg-background-tertiary transition-colors">
              <Settings className="w-5 h-5" />
            </button>
            <button className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-foreground-secondary hover:text-foreground hover:bg-background-tertiary transition-colors">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary-500 to-accent-cyan flex items-center justify-center">
                <User className="w-4 h-4 text-white" />
              </div>
              <span className="hidden sm:inline">张凯</span>
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-background border-t border-border z-50">
        <div className="h-full flex items-center justify-around px-4">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
            
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'flex flex-col items-center gap-1 px-3 py-2 rounded-lg transition-colors',
                  isActive
                    ? 'text-primary-400'
                    : 'text-foreground-secondary'
                )}
              >
                <Icon className="w-5 h-5" />
                <span className="text-xs">{item.name.slice(0, 4)}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Main Content */}
      <main className="pt-16 pb-16 md:pb-0 min-h-screen">
        <div className="p-4 lg:p-6 max-w-7xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
