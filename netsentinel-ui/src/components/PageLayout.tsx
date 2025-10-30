import React, { useState, useCallback } from 'react';
import Header from './Header';
import SidebarNav from './SidebarNav';

interface PageLayoutProps {
  children: React.ReactNode;
  className?: string;
  maxWidth?: string;
}

export default function PageLayout({
  children,
  className = '',
  maxWidth = 'max-w-7xl'
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
          {children}
        </main>
      </div>
    </div>
  );
}
