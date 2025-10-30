import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react';
import { captureException, addBreadcrumb } from '@/utils/sentry';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log the error to console
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // Add breadcrumb for debugging
    addBreadcrumb('ErrorBoundary caught error', 'error', 'error');

    // Store error details for debugging
    this.setState({
      error,
      errorInfo
    });

    // Send error to Sentry with React component stack
    captureException(error, {
      componentStack: errorInfo.componentStack,
      errorBoundary: true,
      userAgent: navigator.userAgent,
      url: window.location.href,
    });
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
          <div className="max-w-md w-full">
            <div className="card-dark p-8 text-center space-y-6">
              <div className="flex justify-center">
                <div className="relative">
                  <div className="absolute inset-0 bg-red-500 blur-xl opacity-30 animate-pulse"></div>
                  <AlertTriangle className="relative w-16 h-16 text-red-400" strokeWidth={1.5} />
                </div>
              </div>

              <div className="space-y-3">
                <h1 className="text-2xl font-bold text-gradient">Oops! Something went wrong</h1>
                <p className="text-slate-400 text-sm">
                  We're sorry, but something unexpected happened. Our team has been notified and is working to fix this issue.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <button
                  onClick={this.handleRetry}
                  className="flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Try Again</span>
                </button>

                <button
                  onClick={this.handleGoHome}
                  className="flex items-center justify-center space-x-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 hover:text-white rounded-lg transition-colors"
                >
                  <Home className="w-4 h-4" />
                  <span>Go Home</span>
                </button>
              </div>

              {process.env.NODE_ENV === 'development' && this.state.error && (
                <details className="mt-6 text-left">
                  <summary className="flex items-center space-x-2 cursor-pointer text-slate-400 hover:text-slate-300">
                    <Bug className="w-4 h-4" />
                    <span className="text-sm">Error Details (Development)</span>
                  </summary>
                  <div className="mt-3 p-3 bg-slate-800 rounded-lg text-xs font-mono text-red-300 overflow-auto max-h-40">
                    <div className="font-semibold text-red-400 mb-2">Error:</div>
                    <div className="mb-2">{this.state.error.message}</div>
                    {this.state.errorInfo && (
                      <>
                        <div className="font-semibold text-red-400 mb-2">Component Stack:</div>
                        <pre className="whitespace-pre-wrap">{this.state.errorInfo.componentStack}</pre>
                      </>
                    )}
                  </div>
                </details>
              )}

              <div className="text-center text-xs text-slate-500 pt-4 border-t border-slate-700">
                <p>If this problem persists, please contact support</p>
                <p className="mt-1">Error ID: {Date.now().toString(36)}</p>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Higher-order component for easier usage
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  fallback?: ReactNode
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary fallback={fallback}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;

  return WrappedComponent;
}

// Hook for manual error reporting (for non-React errors)
// moved to src/hooks/useErrorReporting.ts
export { useErrorReporting } from '@/hooks/useErrorReporting';
