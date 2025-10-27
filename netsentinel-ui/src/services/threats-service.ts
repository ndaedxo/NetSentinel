import type { ThreatType } from '@/types';
import { mockRecentThreats, mockThreats, mockThreatTimeline } from '@/mock';

/**
 * Get recent threats
 */
export async function getRecentThreats(): Promise<ThreatType[]> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));
  return mockRecentThreats;
}

/**
 * Get all threats
 */
export async function getAllThreats(): Promise<ThreatType[]> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 500));
  return mockThreats;
}

/**
 * Get threat timeline data
 */
export async function getThreatTimeline(): Promise<any[]> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 200));
  return mockThreatTimeline;
}

/**
 * Block a threat by IP address
 */
export async function blockThreat(_ipAddress: string): Promise<{ success: boolean }> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));
  return { success: true };
}
