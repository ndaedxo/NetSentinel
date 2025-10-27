import type { DashboardMetrics, SystemHealthService } from '@/types';
import { mockDashboardMetrics, mockSystemHealth } from '@/mock';

/**
 * Get dashboard metrics
 */
export async function getDashboardMetrics(): Promise<DashboardMetrics> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 500));
  return mockDashboardMetrics;
}

/**
 * Get system health status
 */
export async function getSystemHealth(): Promise<{ services: SystemHealthService[] }> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));
  return mockSystemHealth;
}
