import type { AlertType } from '@/types';
import { mockActiveAlerts, mockAlerts } from '@/mock';

/**
 * Get active alerts
 */
export async function getActiveAlerts(): Promise<AlertType[]> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 200));
  return mockActiveAlerts;
}

/**
 * Get all alerts
 */
export async function getAllAlerts(): Promise<AlertType[]> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 400));
  return mockAlerts;
}

/**
 * Acknowledge an alert
 */
export async function acknowledgeAlert(_alertId: number): Promise<{ success: boolean }> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));
  return { success: true };
}

/**
 * Resolve an alert
 */
export async function resolveAlert(_alertId: number): Promise<{ success: boolean }> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));
  return { success: true };
}
