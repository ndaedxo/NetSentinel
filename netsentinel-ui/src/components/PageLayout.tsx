import React, { useState, useCallback } from 'react';
import Header from './Header';
import SidebarNav from './SidebarNav';

interface PageLayoutProps {
  children: React.ReactNode;
  className?: string;
  maxWidth?: string;
  title?: string;
  subtitle?: string;
}

export default function PageLayout({
  children,
  className = '',
  maxWidth = 'max-w-7xl',
  title,
  subtitle,
}: PageLayoutProps) {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const toggleSidebar = useCallback(() => {
    setIsSidebarCollapsed((v) => !v);
  }, []);
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex">
      <SidebarNav collapsed={isSidebarCollapsed} />
      <div className="flex-1 min-w-0 flex flex-col">
        <Header onToggleSidebar={toggleSidebar} isSidebarCollapsed={isSidebarCollapsed} />
        <main className={`${maxWidth} mx-auto px-6 py-8 ${className}`}>
          {(title || subtitle) && (
            <div className="mb-6">
              {title && <h1 className="text-2xl font-semibold text-white">{title}</h1>}
              {subtitle && <p className="text-slate-400 mt-1">{subtitle}</p>}
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}
