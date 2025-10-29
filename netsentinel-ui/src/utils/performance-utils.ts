/**
 * Performance measurement utilities
 */

/**
 * Get page load time in seconds
 */
export function getPageLoadTime(): number {
  const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
  return navigation ? (navigation.loadEventEnd - navigation.fetchStart) / 1000 : 0;
}

/**
 * Get DOM content loaded time in seconds
 */
export function getDomContentLoadedTime(): number {
  const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
  return navigation ? (navigation.domContentLoadedEventEnd - navigation.fetchStart) / 1000 : 0;
}

/**
 * Get first paint time in milliseconds
 */
export function getFirstPaintTime(): number {
  const paint = performance.getEntriesByType('paint').find(entry => entry.name === 'first-paint');
  return paint ? paint.startTime : 0;
}

/**
 * Get largest contentful paint time in milliseconds
 */
export function getLargestContentfulPaint(): number {
  const lcp = performance.getEntriesByType('largest-contentful-paint')[0] as PerformanceEntry & { startTime: number };
  return lcp ? lcp.startTime : 0;
}

/**
 * Get simulated average API response time (in a real app, this would track actual requests)
 */
export function getAverageApiResponseTime(): number {
  // This would need to be tracked separately in a real app
  // For demo purposes, return a simulated value
  return Math.random() * 500 + 200; // 200-700ms
}

/**
 * Get network request count
 */
export function getNetworkRequestCount(): number {
  return performance.getEntriesByType('resource').length;
}

/**
 * Get failed request count (simulated)
 */
export function getFailedRequestCount(): number {
  // This would need to track actual failed requests
  return Math.floor(Math.random() * 3); // 0-2 for demo
}

/**
 * Get used memory in bytes
 */
export function getUsedMemory(): number {
  // @ts-expect-error - performance.memory is not in types but available in Chrome
  return performance.memory?.usedJSHeapSize || 0;
}

/**
 * Get total memory in bytes
 */
export function getTotalMemory(): number {
  // @ts-expect-error - performance.memory is not in types but available in Chrome
  return performance.memory?.totalJSHeapSize || 0;
}

/**
 * Get memory usage percentage
 */
export function getMemoryUsagePercent(): number {
  const used = getUsedMemory();
  const total = getTotalMemory();
  return total > 0 ? (used / total) * 100 : 0;
}

/**
 * Calculate average from an array of numbers
 */
export function calculateAverage(numbers: number[]): number {
  if (numbers.length === 0) return 0;
  return numbers.reduce((sum, num) => sum + num, 0) / numbers.length;
}

