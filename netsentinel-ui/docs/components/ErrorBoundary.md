# ErrorBoundary Component

A React Error Boundary component that catches JavaScript errors anywhere in the component tree, logs them, and displays a fallback UI.

## Features

- Catches React component errors
- Integrates with Sentry for error reporting
- Provides user-friendly error messages
- Shows detailed error information in development
- Allows users to retry or navigate away

## Usage

### Basic Usage

```tsx
import { ErrorBoundary } from '@/components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <YourComponent />
    </ErrorBoundary>
  );
}
```

### With Custom Fallback

```tsx
import { ErrorBoundary } from '@/components/ErrorBoundary';

const CustomFallback = () => (
  <div className="error-fallback">
    <h2>Something went wrong</h2>
    <p>Please try refreshing the page</p>
  </div>
);

function App() {
  return (
    <ErrorBoundary fallback={<CustomFallback />}>
      <YourComponent />
    </ErrorBoundary>
  );
}
```

## Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `children` | `ReactNode` | Yes | - | Child components to wrap |
| `fallback` | `ReactNode` | No | - | Custom fallback UI component |

## Error Reporting

Errors are automatically reported to Sentry with:
- Error message and stack trace
- Component stack (React error boundaries)
- User agent and URL
- User context (if authenticated)
- Custom tags and context

## Development Mode

In development (`NODE_ENV === 'development'`), the error boundary shows:
- Error message and stack trace
- Component stack information
- Collapsible details section

## Production Mode

In production, the error boundary shows:
- User-friendly error message
- Retry and "Go Home" buttons
- Error ID for support reference

## Methods

### componentDidCatch(error, errorInfo)

Called when an error is caught. This method:
1. Logs the error to console
2. Adds a breadcrumb to Sentry
3. Stores error details for display
4. Sends error to Sentry with context

### handleRetry()

Resets the error boundary state, allowing the user to retry rendering the failed component.

### handleGoHome()

Navigates the user back to the home/dashboard page.

## Hooks

### useErrorReporting()

Hook for manual error reporting outside of React components.

```tsx
import { useErrorReporting } from '@/components/ErrorBoundary';

function MyComponent() {
  const { reportError, reportMessage } = useErrorReporting();

  const handleError = (error: Error) => {
    reportError(error, { context: 'user action' });
  };

  const logMessage = () => {
    reportMessage('User completed action', 'info', { action: 'save' });
  };

  return (
    // component JSX
  );
}
```

## Styling

The component uses a dark theme consistent with the application:
- Slate color scheme
- Card-based layout
- Responsive design
- Accessible color contrast

## Testing

Error boundaries are difficult to test directly in unit tests. Integration tests should verify:
- Error UI displays correctly
- Retry functionality works
- Navigation works as expected

## Best Practices

1. Wrap top-level components with ErrorBoundary
2. Use multiple boundaries for different sections
3. Provide meaningful fallback UIs
4. Log errors appropriately for your environment
5. Test error scenarios in development
