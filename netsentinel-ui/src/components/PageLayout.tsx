import React from 'react';
import Header from './Header';

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
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <Header />
      <main className={`${maxWidth} mx-auto px-6 py-8 ${className}`}>
        {children}
      </main>
    </div>
  );
}
