// Jest setup file for React Testing Library
require('@testing-library/jest-dom');

// Configure axe for accessibility testing
const { configureAxe } = require('jest-axe');

configureAxe({
  rules: {
    // Disable rules that are not relevant for component testing
    'color-contrast': { enabled: false },
    'document-title': { enabled: false },
    'html-has-lang': { enabled: false },
    'landmark-one-main': { enabled: false },
    'page-has-heading-one': { enabled: false },
    'region': { enabled: false },
  },
  // Only run checks that are relevant for components
  checks: {
    'autocomplete-valid': { enabled: false },
    'dlitem': { enabled: false },
    'listitem': { enabled: false },
  },
});

// Polyfill for TextEncoder/TextDecoder (needed for jsPDF)
global.TextEncoder = require('util').TextEncoder;
global.TextDecoder = require('util').TextDecoder;

// Mock import.meta.env
global.import = global.import || {};
global.import.meta = global.import.meta || {};
global.import.meta.env = {
  VITE_SENTRY_DSN: 'test-dsn',
  ...global.import.meta.env,
};

// Mock window.matchMedia (required for some UI libraries)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock IntersectionObserver
global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));
