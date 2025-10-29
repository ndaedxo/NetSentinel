import React from 'react';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export default function LoadingSpinner({
  message = 'Loading...',
  size = 'md',
  className = ''
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-12 h-12',
    lg: 'w-16 h-16'
  };

  return (
    <div className={`min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center ${className}`}>
      <div className="flex flex-col items-center space-y-4">
        <div className={`border-4 border-blue-500 border-t-transparent rounded-full animate-spin ${sizeClasses[size]}`}></div>
        <p className="text-slate-400">{message}</p>
      </div>
    </div>
  );
}
