import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';
import {
  getPageLoadTime,
  getDomContentLoadedTime,
  getFirstPaintTime,
  getLargestContentfulPaint,
  getAverageApiResponseTime,
  getNetworkRequestCount,
  getFailedRequestCount,
  getUsedMemory,
  getTotalMemory,
  getMemoryUsagePercent,
  calculateAverage
} from '../performance-utils';
import { formatBytes } from '../format-util';

// Mock objects
const mockPerformance = {
  getEntriesByType: jest.fn(),
  now: jest.fn(() => Date.now()),
  timing: {
    loadEventEnd: 2000,
    fetchStart: 1000,
    domContentLoadedEventEnd: 1500
  }
};

const mockMemory = {
  usedJSHeapSize: 50 * 1024 * 1024, // 50MB
  totalJSHeapSize: 100 * 1024 * 1024 // 100MB
};

describe('Performance Utils', () => {
  beforeEach(() => {
    // Mock the global performance API
    Object.defineProperty(window, 'performance', {
      value: mockPerformance,
      writable: true
    });

    // Mock performance.memory
    Object.defineProperty(window.performance, 'memory', {
      value: mockMemory,
      writable: true
    });

    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Page Load Metrics', () => {
    it('calculates page load time correctly', () => {
      mockPerformance.getEntriesByType.mockReturnValue([{
        loadEventEnd: 2000,
        fetchStart: 1000
      }]);

      const result = getPageLoadTime();
      expect(result).toBe(1.0); // (2000 - 1000) / 1000 = 1 second
    });

    it('returns 0 when navigation timing is not available', () => {
      mockPerformance.getEntriesByType.mockReturnValue([]);

      const result = getPageLoadTime();
      expect(result).toBe(0);
    });

    it('calculates DOM content loaded time correctly', () => {
      mockPerformance.getEntriesByType.mockReturnValue([{
        domContentLoadedEventEnd: 1500,
        fetchStart: 1000
      }]);

      const result = getDomContentLoadedTime();
      expect(result).toBe(0.5); // (1500 - 1000) / 1000 = 0.5 seconds
    });
  });

  describe('Paint Metrics', () => {
    it('gets first paint time correctly', () => {
      mockPerformance.getEntriesByType.mockReturnValue([{
        name: 'first-paint',
        startTime: 500
      }]);

      const result = getFirstPaintTime();
      expect(result).toBe(500);
    });

    it('returns 0 when first paint is not found', () => {
      mockPerformance.getEntriesByType.mockReturnValue([]);

      const result = getFirstPaintTime();
      expect(result).toBe(0);
    });

    it('gets largest contentful paint time correctly', () => {
      mockPerformance.getEntriesByType.mockReturnValue([{
        startTime: 800
      }]);

      const result = getLargestContentfulPaint();
      expect(result).toBe(800);
    });

    it('returns 0 when LCP is not available', () => {
      mockPerformance.getEntriesByType.mockReturnValue([]);

      const result = getLargestContentfulPaint();
      expect(result).toBe(0);
    });
  });

  describe('API and Network Metrics', () => {
    it('returns simulated API response time', () => {
      const result = getAverageApiResponseTime();

      expect(typeof result).toBe('number');
      expect(result).toBeGreaterThanOrEqual(200);
      expect(result).toBeLessThanOrEqual(700);
    });

    it('counts network requests correctly', () => {
      const mockEntries = [
        { name: 'http://example.com/api/1' },
        { name: 'http://example.com/api/2' },
        { name: 'http://example.com/image.png' }
      ];
      mockPerformance.getEntriesByType.mockReturnValue(mockEntries);

      const result = getNetworkRequestCount();
      expect(result).toBe(3);
    });

    it('returns simulated failed request count', () => {
      const result = getFailedRequestCount();

      expect(typeof result).toBe('number');
      expect(result).toBeGreaterThanOrEqual(0);
      expect(result).toBeLessThanOrEqual(2);
    });
  });

  describe('Memory Metrics', () => {
    it('gets used memory correctly', () => {
      const result = getUsedMemory();
      expect(result).toBe(50 * 1024 * 1024); // 50MB
    });

    it('gets total memory correctly', () => {
      const result = getTotalMemory();
      expect(result).toBe(100 * 1024 * 1024); // 100MB
    });

    it('calculates memory usage percentage correctly', () => {
      const result = getMemoryUsagePercent();
      expect(result).toBe(50); // 50MB used out of 100MB total = 50%
    });

    it('returns 0 when total memory is 0', () => {
      // Temporarily override memory
      Object.defineProperty(window.performance, 'memory', {
        value: {
          usedJSHeapSize: 10 * 1024 * 1024,
          totalJSHeapSize: 0
        },
        writable: true
      });

      const result = getMemoryUsagePercent();
      expect(result).toBe(0);
    });
  });

  describe('Utility Functions', () => {
    it('formats bytes correctly', () => {
      expect(formatBytes(0)).toBe('0 Bytes');
      expect(formatBytes(1024)).toBe('1 KB');
      expect(formatBytes(1024 * 1024)).toBe('1 MB');
      expect(formatBytes(1024 * 1024 * 1024)).toBe('1 GB');
    });

    it('calculates average correctly', () => {
      expect(calculateAverage([1, 2, 3, 4, 5])).toBe(3);
      expect(calculateAverage([10, 20, 30])).toBe(20);
      expect(calculateAverage([])).toBe(0);
      expect(calculateAverage([5])).toBe(5);
    });
  });
});
