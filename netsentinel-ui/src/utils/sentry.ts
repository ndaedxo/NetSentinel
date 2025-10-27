import * as Sentry from '@sentry/react';
import { BrowserTracing } from '@sentry/tracing';

export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  const environment = import.meta.env.VITE_SENTRY_ENVIRONMENT || 'development';

  // Only initialize Sentry if DSN is provided
  if (!dsn || dsn === 'https://your-sentry-dsn-here@sentry.io/project-id') {
    console.log('Sentry DSN not configured, skipping Sentry initialization');
    return;
  }

  Sentry.init({
    dsn,
    environment,
    integrations: [
      new BrowserTracing({
        // Set 'tracePropagationTargets' to control for which URLs distributed tracing should be enabled
        tracePropagationTargets: ['localhost', /^https:\/\/your-site\.com/],
      }),
      new Sentry.Replay({
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
    release: import.meta.env.VITE_APP_VERSION || '1.0.0',

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
        version: import.meta.env.VITE_APP_VERSION || '1.0.0',
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

export function captureException(error: Error, context?: Record<string, any>) {
  Sentry.withScope((scope) => {
    if (context) {
      Object.keys(context).forEach((key) => {
        scope.setTag(key, context[key]);
      });
    }
    Sentry.captureException(error);
  });
}

export function captureMessage(message: string, level: Sentry.SeverityLevel = 'info', context?: Record<string, any>) {
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

// Performance monitoring helper
export function startTransaction(name: string, op: string) {
  return Sentry.startTransaction({ name, op });
}
