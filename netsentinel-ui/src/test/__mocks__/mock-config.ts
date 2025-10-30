/**
 * Configurable Mock System
 * Allows tests to control mock behavior dynamically
 */

import { MockGenerator, MockStore } from './mock-generator';

// Mock behavior configuration
export interface MockBehaviorConfig {
  /** Enable/disable realistic delays */
  realisticDelays?: boolean;
  /** Enable/disable random errors */
  randomErrors?: boolean;
  /** Error probability (0-1) */
  errorProbability?: number;
  /** Data variability factor */
  variability?: number;
  /** Enable/disable time-based progression */
  timeBased?: boolean;
  /** Force specific error types */
  forceErrors?: ('network' | 'auth' | 'validation' | 'server')[];
  /** Custom delay ranges */
  delayRanges?: {
    threats?: { min: number; max: number };
    alerts?: { min: number; max: number };
    default?: { min: number; max: number };
  };
  /** Data seeding for consistent results */
  seed?: number;
}

/**
 * Mock Configuration Manager
 * Controls global mock behavior across all services
 */
export class MockConfigManager {
  private static instance: MockConfigManager;
  private config: MockBehaviorConfig;
  private stores: Map<string, MockStore> = new Map();

  private constructor() {
    // Set development-friendly defaults
    this.config = {
      realisticDelays: false, // No delays in development
      randomErrors: false,    // No random errors in development
      variability: 0.3,
      timeBased: true,
      delayRanges: {
        threats: { min: 0, max: 0 },
        alerts: { min: 0, max: 0 },
        default: { min: 0, max: 0 }
      }
    };
  }

  static getInstance(): MockConfigManager {
    if (!MockConfigManager.instance) {
      MockConfigManager.instance = new MockConfigManager();
    }
    return MockConfigManager.instance;
  }

  /**
   * Configure mock behavior globally
   */
  configure(config: MockBehaviorConfig): void {
    // If realisticDelays is enabled but no delayRanges provided, set defaults
    if (config.realisticDelays && !config.delayRanges) {
      config.delayRanges = {
        threats: { min: 300, max: 1200 },
        alerts: { min: 200, max: 800 },
        default: { min: 100, max: 500 }
      };
    }

    this.config = { ...this.config, ...config };

    // Update all existing stores
    for (const store of this.stores.values()) {
      this.updateStoreConfig(store);
    }
  }

  /**
   * Get current configuration
   */
  getConfig(): MockBehaviorConfig {
    return { ...this.config };
  }

  /**
   * Reset to default configuration
   */
  reset(): void {
    // Reset to development-friendly defaults
    this.config = {
      realisticDelays: false,
      randomErrors: false,
      variability: 0.3,
      timeBased: true,
      delayRanges: {
        threats: { min: 0, max: 0 },
        alerts: { min: 0, max: 0 },
        default: { min: 0, max: 0 }
      }
    };
    // Reset all stores
    for (const store of this.stores.values()) {
      store.reset();
      this.updateStoreConfig(store);
    }
  }

  /**
   * Get or create a mock store for a specific domain
   */
  getStore(domain: string): MockStore {
    if (!this.stores.has(domain)) {
      const store = new MockStore();
      this.stores.set(domain, store);
      this.updateStoreConfig(store);
    }
    return this.stores.get(domain)!;
  }

  /**
   * Update store configuration based on global config
   */
  private updateStoreConfig(store: MockStore): void {
    // Update threat generator
    const threatGen = store.getGenerator('threats');
    if (threatGen) {
      threatGen.configure(this.config);
    }

    // Update alert generator
    const alertGen = store.getGenerator('alerts');
    if (alertGen) {
      alertGen.configure(this.config);
    }
  }

  /**
   * Force next operation to fail with specific error
   */
  forceNextError(errorType: 'network' | 'auth' | 'validation' | 'server'): void {
    const errors = this.config.forceErrors || [];
    errors.push(errorType);
    this.config.forceErrors = errors;
  }

  /**
   * Clear forced errors
   */
  clearForcedErrors(): void {
    this.config.forceErrors = [];
  }

  /**
   * Enable error simulation for next N operations
   */
  enableErrorsForNext(count: number, errorType: 'network' | 'auth' | 'validation' | 'server' = 'server'): void {
    for (let i = 0; i < count; i++) {
      this.forceNextError(errorType);
    }
  }

  /**
   * Set custom delays for specific operations
   */
  setCustomDelays(delays: MockBehaviorConfig['delayRanges']): void {
    this.config.delayRanges = { ...this.config.delayRanges, ...delays };
  }

  /**
   * Get delay range for a specific domain
   */
  getDelayRange(domain: string): { min: number; max: number } {
    const ranges = this.config.delayRanges;
    const defaultRange = ranges?.default || { min: 100, max: 500 };

    switch (domain) {
      case 'threats':
        return ranges?.threats || defaultRange;
      case 'alerts':
        return ranges?.alerts || defaultRange;
      default:
        return defaultRange;
    }
  }
}

// Extend MockGenerator to support configuration
declare module './mock-generator' {
  interface MockGenerator {
    configure(config: MockBehaviorConfig): void;
    getForcedError(): 'network' | 'auth' | 'validation' | 'server' | null;
  }
}

// Add configuration methods to MockGenerator
Object.assign(MockGenerator.prototype, {
  configure(this: MockGenerator, config: MockBehaviorConfig): void {
    Object.assign(this, {
      realisticDelays: config.realisticDelays ?? this.realisticDelays,
      randomErrors: config.randomErrors ?? this.randomErrors,
      errorProbability: config.errorProbability ?? this.errorProbability,
      variability: config.variability ?? this.variability,
      timeBased: config.timeBased ?? this.timeBased,
    });

    // Set faker seed if provided
    if (config.seed !== undefined && typeof (global as { faker?: { seed: (seed: number) => void } }).faker !== 'undefined') {
      (global as { faker?: { seed: (seed: number) => void } }).faker!.seed(config.seed);
    }
  },

  getForcedError(this: MockGenerator): 'network' | 'auth' | 'validation' | 'server' | null {
    const manager = MockConfigManager.getInstance();
    const config = manager.getConfig();
    if (config.forceErrors && config.forceErrors.length > 0) {
      // Peek at the next error without removing it
      return config.forceErrors[0];
    }
    return null;
  }
});

// Update MockGenerator's shouldError method to use forced errors
const originalShouldError = MockGenerator.prototype.shouldError;
MockGenerator.prototype.shouldError = function() {
  const forcedError = this.getForcedError();
  if (forcedError) {
    return true;
  }
  return originalShouldError.call(this);
};

// Update MockGenerator's generateError method to use forced errors
const originalGenerateError = MockGenerator.prototype.generateError;
MockGenerator.prototype.generateError = function(type) {
  const manager = MockConfigManager.getInstance();
  const config = manager.getConfig();
  if (config.forceErrors && config.forceErrors.length > 0) {
    // Consume the forced error
    const forcedError = config.forceErrors.shift()!;
    return originalGenerateError.call(this, forcedError);
  }
  return originalGenerateError.call(this, type);
};

// Update MockGenerator's delay method to respect configuration
const _originalDelay = MockGenerator.prototype.delay;
MockGenerator.prototype.delay = function(minMs: number, maxMs: number): Promise<void> {
  const manager = MockConfigManager.getInstance();
  const config = manager.getConfig();

  if (!config.realisticDelays) return Promise.resolve();

  const delay = Math.random() * (maxMs - minMs) + minMs;
  return new Promise(resolve => setTimeout(resolve, delay));
};

// Global mock manager instance
export const mockConfig = MockConfigManager.getInstance();

/**
 * Test utilities for controlling mock behavior
 */
export const mockUtils = {
  /**
   * Configure mocks for all tests
   */
  setup(config: MockBehaviorConfig = {}): void {
    mockConfig.configure(config);
  },

  /**
   * Reset mocks to default state
   */
  reset(): void {
    mockConfig.reset();
  },

  /**
   * Enable error simulation for next operations
   */
  simulateErrors(count: number = 1, type: 'network' | 'auth' | 'validation' | 'server' = 'server'): void {
    mockConfig.enableErrorsForNext(count, type);
  },

  /**
   * Force specific error on next operation
   */
  forceError(type: 'network' | 'auth' | 'validation' | 'server'): void {
    mockConfig.forceNextError(type);
  },

  /**
   * Set custom delays
   */
  setDelays(delays: MockBehaviorConfig['delayRanges']): void {
    mockConfig.setCustomDelays(delays);
  },

  /**
   * Disable delays for faster tests
   */
  disableDelays(): void {
    mockConfig.configure({ realisticDelays: false });
  },

  /**
   * Enable realistic delays
   */
  enableDelays(): void {
    mockConfig.configure({ realisticDelays: true });
  },

  /**
   * Set consistent seed for reproducible tests
   */
  setSeed(seed: number): void {
    mockConfig.configure({ seed });
  },

  /**
   * Get current mock store for direct manipulation
   */
  getStore(domain: string = 'default'): MockStore {
    return mockConfig.getStore(domain);
  }
};

// Jest setup helper
export const setupMockTests = (config: MockBehaviorConfig = {}) => {
  beforeEach(() => {
    mockConfig.reset();
    mockConfig.configure(config);
  });

  afterEach(() => {
    mockConfig.clearForcedErrors();
  });
};

