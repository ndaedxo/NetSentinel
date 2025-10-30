import type { ThreatType } from '@/types';
import { mockConfig } from '@/test/__mocks__/mock-config';

/**
 * Get recent threats with dynamic data
 */
export async function getRecentThreats(count: number = 10): Promise<ThreatType[]> {
  const store = mockConfig.getStore('threats');
  const delayRange = mockConfig.getDelayRange('threats');

  // Simulate realistic API delay if enabled
  await store.getGenerator('threats').delay(delayRange.min, delayRange.max);

  // Check for simulated errors
  if (store.getGenerator('threats').shouldError()) {
    throw store.getGenerator('threats').generateError('network');
  }

  return store.getRecentThreats(count);
}

/**
 * Get all threats with dynamic data
 */
export async function getAllThreats(): Promise<ThreatType[]> {
  const store = mockConfig.getStore('threats');
  const delayRange = mockConfig.getDelayRange('threats');

  // Simulate realistic API delay if enabled
  await store.getGenerator('threats').delay(delayRange.min * 1.5, delayRange.max * 1.5);

  // Check for simulated errors
  if (store.getGenerator('threats').shouldError()) {
    throw store.getGenerator('threats').generateError('server');
  }

  return store.getAllThreats();
}

/**
 * Get threat timeline data with time-based generation
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function getThreatTimeline(_hours: number = 24): Promise<Array<{timestamp: string; threat_count: number; blocked_count: number}>> {
  const store = mockConfig.getStore('threats');
  const delayRange = mockConfig.getDelayRange('threats');

  // Simulate realistic API delay if enabled
  await store.getGenerator('threats').delay(delayRange.min * 0.75, delayRange.max * 0.75);

  // Check for simulated errors
  if (store.getGenerator('threats').shouldError()) {
    throw store.getGenerator('threats').generateError('network');
  }

  return store.getTimelineData();
}

/**
 * Block a threat by IP address with state management
 */
export async function blockThreat(ipAddress: string): Promise<{ success: boolean }> {
  const store = mockConfig.getStore('threats');

  // Check for simulated errors
  if (store.getGenerator('threats').shouldError()) {
    throw store.getGenerator('threats').generateError('server');
  }

  return store.blockThreat(ipAddress);
}

/**
 * Get threat statistics with dynamic calculation
 */
export async function getThreatStats(): Promise<{
  total: number;
  blocked: number;
  active: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}> {
  const store = mockConfig.getStore('threats');
  const delayRange = mockConfig.getDelayRange('threats');

  // Simulate realistic API delay if enabled
  await store.getGenerator('threats').delay(delayRange.min * 0.5, delayRange.max * 0.5);

  // Check for simulated errors
  if (store.getGenerator('threats').shouldError()) {
    throw store.getGenerator('threats').generateError('network');
  }

  const threats = store.getAllThreats();

  return {
    total: threats.length,
    blocked: threats.filter(t => t.is_blocked === 1).length,
    active: threats.filter(t => t.is_blocked === 0).length,
    critical: threats.filter(t => t.severity === 'critical').length,
    high: threats.filter(t => t.severity === 'high').length,
    medium: threats.filter(t => t.severity === 'medium').length,
    low: threats.filter(t => t.severity === 'low').length,
  };
}
