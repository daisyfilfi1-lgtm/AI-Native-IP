'use client';

import { cn } from '@/lib/utils';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

interface MainLayoutProps {
  children: React.ReactNode;
  title?: string;
  className?: string;
}

export function MainLayout({ children, title, className }: MainLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content：isolate 避免侧栏子项溢出时与主区命中区域重叠 */}
      <div className="ml-64 min-h-screen flex flex-col relative isolate">
        <Header title={title} />
        
        <main className={cn('flex-1 p-6', className)}>
          {children}
        </main>
      </div>
    </div>
  );
}
