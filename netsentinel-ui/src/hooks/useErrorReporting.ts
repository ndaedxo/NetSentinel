export function useErrorReporting() {
  const reportError = (error: Error, context?: Record<string, unknown>) => {
    console.error('Manual error report:', error, context);
    // Send to Sentry
    // Defer import to avoid circular deps
    import('@/utils/sentry').then(({ captureException }) => {
      captureException(error, {
        ...context,
        manual: true,
        userAgent: navigator.userAgent,
        url: window.location.href,
      });
    });
  };

  const reportMessage = (
    message: string,
    level: 'info' | 'warning' | 'error' = 'error',
    context?: Record<string, unknown>
  ) => {
    console.log(`Manual message report [${level}]:`, message, context);
    import('@/utils/sentry').then(({ captureMessage }) => {
      captureMessage(message, level, {
        ...context,
        manual: true,
        userAgent: navigator.userAgent,
        url: window.location.href,
      });
    });
  };

  return { reportError, reportMessage };
}
