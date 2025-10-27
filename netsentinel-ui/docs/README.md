# Netsentinel UI Documentation

## Overview

Netsentinel is a comprehensive security operations center built with React, TypeScript, and modern web technologies. This documentation provides guidance for developers working on the project.

## Architecture

### Technology Stack

- **Frontend Framework**: React 19 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: React Context API
- **Routing**: React Router v7
- **Data Visualization**: Recharts
- **Testing**: Jest + React Testing Library + Playwright (E2E)
- **Error Monitoring**: Sentry
- **Code Quality**: ESLint + TypeScript

### Project Structure

```
src/
├── components/          # Reusable UI components
├── pages/              # Page components (lazy loaded)
├── hooks/              # Custom React hooks
├── services/           # API service functions
├── mock/               # Mock data for development
├── types/              # TypeScript type definitions
├── utils/              # Utility functions
├── test/               # Test utilities
└── styles/             # Global styles
```

## Development

### Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start development server:
   ```bash
   npm run dev
   ```

3. Run tests:
   ```bash
   npm test              # Unit tests
   npm run test:e2e      # E2E tests
   ```

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run build:analyze` - Build with bundle analyzer
- `npm run check` - Type check and build
- `npm run lint` - Run ESLint
- `npm test` - Run unit tests
- `npm run test:watch` - Run tests in watch mode
- `npm run test:coverage` - Run tests with coverage
- `npm run test:e2e` - Run E2E tests

## Key Features

### Authentication

- Mock authentication system for development
- Google OAuth integration (configurable)
- Session persistence with localStorage
- Protected routes

### Error Handling

- Global Error Boundaries
- Sentry integration for error monitoring
- User-friendly error messages
- Development error details

### Performance

- Code splitting with React.lazy()
- Bundle optimization with manual chunks
- Terser minification
- Image optimization

### Testing

- Unit tests with Jest and React Testing Library
- E2E tests with Playwright
- Component testing infrastructure
- CI/CD ready test setup

## Components

### Core Components

#### StatCard
Displays key metrics with icons and trend indicators.

```tsx
<StatCard
  title="Total Events"
  value={1234}
  icon={Activity}
  trend={{ value: "12%", isPositive: true }}
  color="blue"
/>
```

#### ErrorBoundary
Catches React errors and provides fallback UI.

```tsx
<ErrorBoundary fallback={<CustomFallback />}>
  <YourComponent />
</ErrorBoundary>
```

#### Header
Application header with navigation and user menu.

#### AlertFeed
Real-time alert display component.

### Hooks

#### useApi
Generic hook for API calls with loading and error states.

```tsx
const { data, loading, error, refetch } = useApi('/api/threats');
```

#### useAuth
Authentication hook providing user state and auth methods.

```tsx
const { user, login, logout, isPending } = useAuth();
```

#### useErrorReporting
Hook for manual error reporting.

```tsx
const { reportError, reportMessage } = useErrorReporting();
```

## API Integration

### Service Layer

All API calls go through the service layer in `src/services/`. Services return mock data in development.

### Mock Data

Mock data is stored in `src/mock/` and provides realistic data for development and testing.

## Styling

### Design System

- **Colors**: Slate-based dark theme
- **Typography**: Clean, readable fonts
- **Spacing**: Consistent spacing scale
- **Components**: Card-based layout system

### CSS Classes

Common utility classes:
- `card-dark` - Dark card with border and shadow
- `text-gradient` - Blue gradient text
- `glow-blue` - Blue glow effect

## Deployment

### Environment Variables

Copy `.env-example` to `.env` and configure:

```env
# Development settings
NODE_ENV=development

# Sentry Error Monitoring
VITE_SENTRY_DSN=https://your-sentry-dsn-here@sentry.io/project-id
VITE_SENTRY_ENVIRONMENT=development
```

### Build Process

1. Type checking: `tsc`
2. Linting: `eslint`
3. Testing: `jest` + Playwright
4. Build: `vite build`
5. Bundle analysis: `vite build --mode analyze`

## Contributing

### Code Style

- Use TypeScript for all new code
- Follow ESLint configuration
- Write tests for new features
- Use semantic commit messages

### Testing Strategy

1. Unit tests for components and utilities
2. Integration tests for hooks and services
3. E2E tests for critical user journeys
4. Visual regression tests (future)

### Performance Guidelines

- Lazy load page components
- Optimize bundle size
- Use React.memo for expensive components
- Monitor Core Web Vitals

## Troubleshooting

### Common Issues

1. **Build fails with dependency conflicts**
   - Run `npm install --legacy-peer-deps`

2. **Sentry not reporting errors**
   - Check VITE_SENTRY_DSN environment variable
   - Verify DSN format

3. **Tests failing**
   - Ensure Playwright browsers are installed: `npx playwright install`
   - Check test environment setup

4. **TypeScript errors**
   - Run `npm run check` to see all type errors
   - Check import paths and type definitions

## Support

For development support:
- Check existing documentation
- Review component examples
- Run tests to understand expected behavior
- Check Sentry for runtime errors
