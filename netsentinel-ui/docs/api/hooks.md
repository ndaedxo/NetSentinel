# Custom Hooks API

## useApi Hook

A generic React hook for fetching data from APIs with loading states, error handling, and automatic refreshing.

### Usage

```tsx
import { useApi } from '@/hooks';

function Dashboard() {
  // Fetch data on mount
  const { data, loading, error } = useApi('/api/dashboard');

  // With refresh interval
  const { data: threats, refetch } = useApi('/api/threats', 30000); // 30s

  // With service function
  const { data: alerts } = useApi(() => getAlerts());

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return <div>{/* render data */}</div>;
}
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `endpointOrService` | `string \| () => Promise<T>` | Yes | - | API endpoint string or service function |
| `refreshInterval` | `number` | No | - | Auto-refresh interval in milliseconds |

### Return Value

```tsx
{
  data: T | null,           // Fetched data
  loading: boolean,         // Loading state
  error: string | null,     // Error message
  refetch: () => Promise<void>, // Manual refetch function
  fetchData: <U = T>(overrideEndpoint?: string) => Promise<U>, // Direct fetch
  postData: (endpoint: string, body?: any) => Promise<any>     // POST request
}
```

### Features

- **Automatic Loading States**: Tracks loading state during requests
- **Error Handling**: Provides user-friendly error messages
- **Auto-refresh**: Optional polling with configurable intervals
- **Manual Refetch**: Ability to manually trigger data refresh
- **Flexible API**: Supports both endpoint strings and service functions
- **TypeScript Support**: Full type safety for return data

## useAuth Hook

Authentication hook providing user state, login/logout functionality, and OAuth support.

### Usage

```tsx
import { useAuth } from '@/hooks';

function Header() {
  const { user, login, logout, isPending } = useAuth();

  const handleLogin = async (email: string, password: string) => {
    try {
      await login(email, password);
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  if (isPending) return <div>Loading...</div>;

  return user ? (
    <div>Welcome, {user.name}!</div>
  ) : (
    <button onClick={() => handleLogin('user@example.com', 'password')}>
      Login
    </button>
  );
}
```

### Return Value

```tsx
{
  user: User | null,        // Current user object
  isPending: boolean,       // Authentication operation in progress
  login: (email: string, password: string) => Promise<void>,
  logout: () => Promise<void>,
  redirectToLogin: () => void,  // OAuth redirect
  exchangeCodeForSessionToken: (code: string) => Promise<void>
}
```

### User Object

```tsx
interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
}
```

### Features

- **Session Persistence**: Maintains login state across browser sessions
- **Mock Authentication**: Demo authentication (accepts any email/password)
- **OAuth Support**: Google OAuth integration
- **Error Handling**: Comprehensive error handling for auth operations
- **Loading States**: Tracks authentication operations

## useErrorReporting Hook

Hook for manual error reporting and logging outside of React error boundaries.

### Usage

```tsx
import { useErrorReporting } from '@/components/ErrorBoundary';

function DataProcessor() {
  const { reportError, reportMessage } = useErrorReporting();

  const processData = async (data: any) => {
    try {
      // Process data
      await riskyOperation(data);
      reportMessage('Data processed successfully', 'info', {
        recordCount: data.length
      });
    } catch (error) {
      reportError(error as Error, {
        operation: 'data-processing',
        inputSize: data.length
      });
      throw error;
    }
  };

  return (
    <button onClick={() => processData(someData)}>
      Process Data
    </button>
  );
}
```

### Return Value

```tsx
{
  reportError: (error: Error, context?: Record<string, any>) => void,
  reportMessage: (message: string, level?: 'info' | 'warning' | 'error', context?: Record<string, any>) => void
}
```

### Features

- **Sentry Integration**: Automatically reports to Sentry with context
- **Flexible Context**: Attach custom metadata to reports
- **Multiple Levels**: Support for info, warning, and error messages
- **User Context**: Includes user information when available
- **Environment Aware**: Adjusts reporting based on environment

## useOnboardingTour Hook

Hook for managing the interactive onboarding tour experience.

### Usage

```tsx
import { useOnboardingTour } from '@/components/OnboardingTour';

function HelpSection() {
  const { startTour, resetTour } = useOnboardingTour();

  return (
    <div>
      <button onClick={startTour}>
        Take Tour
      </button>
      <button onClick={resetTour}>
        Reset Tour
      </button>
    </div>
  );
}
```

### Return Value

```tsx
{
  startTour: () => void,    // Start the onboarding tour
  resetTour: () => void     // Reset tour completion status
}
```

### Features

- **Automatic Trigger**: Shows tour for first-time users
- **Manual Control**: Allow users to restart tour anytime
- **Persistent State**: Remembers tour completion across sessions
- **Customizable Steps**: Tour steps defined in OnboardingTour component
