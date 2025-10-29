import * as Sentry from '@sentry/react';

// Handle test environment where import.meta might not be available
const getEnvVar = (key: string, defaultValue?: string) => {
  // Check if we're in a test environment (Jest sets several environment variables)
  if (typeof process !== 'undefined' &&
      (process.env?.JEST_WORKER_ID || process.env?.NODE_ENV === 'test')) {
    return defaultValue;
  }

  // Only access import.meta in non-test environments
  try {
    // Use eval to avoid TypeScript compilation issues with import.meta
    const env = eval('import.meta?.env?.[key]') || defaultValue;
    return env;
  } catch {
    return defaultValue;
  }
};

export function initSentry() {
  const dsn = getEnvVar('VITE_SENTRY_DSN');
  const environment = getEnvVar('VITE_SENTRY_ENVIRONMENT', 'development');

  // Only initialize Sentry if DSN is provided
  if (!dsn || dsn === 'https://your-sentry-dsn-here@sentry.io/project-id') {
    console.log('Sentry DSN not configured, skipping Sentry initialization');
    return;
  }

  Sentry.init({
    dsn,
    environment,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        // Capture replays for 10% of all sessions
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    // Performance Monitoring
    tracesSampleRate: environment === 'production' ? 0.1 : 1.0, // Capture 100% of transactions in development, 10% in production
    // Session Replay
    replaysSessionSampleRate: environment === 'production' ? 0.1 : 0.1, // 10% of sessions
    replaysOnErrorSampleRate: 1.0, // 100% of sessions with an error

    // Release tracking
    release: getEnvVar('VITE_APP_VERSION', '1.0.0'),

    // Error filtering
    beforeSend(event, hint) {
      // Filter out common non-actionable errors
      const error = hint.originalException as Error;
      if (error?.message?.includes('Loading chunk')) {
        return null; // Filter out chunk loading errors
      }
      if (error?.message?.includes('Network Error') && error?.message?.includes('fetch')) {
        // Only report network errors in production
        if (environment !== 'production') {
          return null;
        }
      }
      return event;
    },

    // User context (will be set when user logs in)
    initialScope: {
      tags: {
        app: 'netsentinel-ui',
        version: getEnvVar('VITE_APP_VERSION', '1.0.0'),
      },
    },
  });

  console.log(`Sentry initialized for environment: ${environment}`);
}

export function setUserContext(user: { id: string; email: string; name?: string; role?: string }) {
  Sentry.setUser({
    id: user.id,
    email: user.email,
    username: user.name,
    role: user.role,
  });
}

export function clearUserContext() {
  Sentry.setUser(null);
}

export function captureException(error: Error, context?: Record<string, unknown>) {
  Sentry.withScope((scope) => {
    if (context) {
      Object.keys(context).forEach((key) => {
        scope.setTag(key, context[key]);
      });
    }
    Sentry.captureException(error);
  });
}

export function captureMessage(message: string, level: Sentry.SeverityLevel = 'info', context?: Record<string, unknown>) {
  Sentry.withScope((scope) => {
    if (context) {
      Object.keys(context).forEach((key) => {
        scope.setTag(key, context[key]);
      });
    }
    Sentry.captureMessage(message, level);
  });
}

export function addBreadcrumb(message: string, category?: string, level?: Sentry.SeverityLevel) {
  Sentry.addBreadcrumb({
    message,
    category: category || 'custom',
    level: level || 'info',
  });
}

// Performance monitoring helper (deprecated - use Sentry directly)
// export function startTransaction(name: string, op: string) {
//   return Sentry.startTransaction({ name, op });
// }
